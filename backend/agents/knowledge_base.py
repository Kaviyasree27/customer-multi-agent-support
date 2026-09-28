"""
Aria Support - Hybrid Retrieval Engine (lexical + dense, fused with RRF)

Pipeline:
1. Query normalisation + phrase-aware synonym expansion
2. Sparse retrieval: word n-gram TF-IDF + character n-gram TF-IDF
3. Dense retrieval: sentence-transformer embeddings (local, optional)
4. Reciprocal Rank Fusion (RRF) of the sparse and dense rankings
5. Optional cross-encoder reranking of the fused candidates
6. Relevance gating so out-of-scope questions return no sources (no forced
   answer -> fewer hallucinations)

The index is cached and only rebuilt when the FAQ collection changes.
Everything runs locally; no paid embedding API is required.
"""

import os

# sentence-transformers only needs PyTorch. Stop it from loading TensorFlow,
# which prints protobuf/keras errors on machines that have both installed.
os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("USE_TORCH", "1")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")

import hashlib
import logging
import re
import threading
from dataclasses import dataclass
from typing import Optional

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from config import Config
from models.feedback_model import list_faqs

log = logging.getLogger("aria.retrieval")


# ============================================================
# CONFIGURATION
# ============================================================

DEFAULT_TOP_K = 3
DEFAULT_MIN_SCORE = 0.12  # lexical relevance gate
MIN_DENSE_SCORE = 0.35  # dense cosine relevance gate
LEXICAL_GATE_WITH_DENSE = 0.35  # stricter lexical gate when dense scores are available

WORD_WEIGHT = 0.65
CHAR_WEIGHT = 0.35

LEXICAL_RRF_WEIGHT = 1.0
DENSE_RRF_WEIGHT = 1.0
RRF_K = 60
RERANK_CANDIDATES = 8

USE_DENSE = getattr(Config, "USE_DENSE_RETRIEVAL", True)
USE_RERANKER = getattr(Config, "USE_RERANKER", False)
EMBEDDING_MODEL = getattr(Config, "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
RERANK_MODEL = getattr(Config, "RERANK_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")


# ============================================================
# QUERY NORMALIZATION
# ============================================================

SYNONYMS = {
    "refund": ["money back", "reimbursement"],
    "return": ["send back", "give back"],
    "replacement": ["exchange", "replace", "another product"],
    "damaged": ["broken", "defective", "cracked"],
    "delivery": ["shipping", "shipment", "arrival"],
    "shipping": ["delivery", "dispatch"],
    "cancel": ["cancellation", "stop order"],
    "payment": ["pay", "transaction"],
    "warranty": ["guarantee", "coverage"],
    "track": ["tracking", "status", "where is"],
    "late": ["delayed", "delay"],
    "product": ["item", "purchase"],
    "customer": ["buyer", "user"],
}


def normalize_text(text):
    if not isinstance(text, str):
        return ""
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text)


def expand_query(query):
    """
    Phrase-aware synonym expansion (handles multi-word synonyms such as
    "money back" -> "refund").
    """
    normalized = normalize_text(query)
    if not normalized:
        return ""

    padded = f" {normalized} "
    extra = []

    for key, alternatives in SYNONYMS.items():
        if f" {key} " in padded:
            extra.extend(alternatives)
        if any(f" {alt} " in padded for alt in alternatives):
            extra.append(key)

    return " ".join([normalized] + extra)


def _prepare_faq_document(faq):
    question = str(faq.get("question", "") or "")
    answer = str(faq.get("answer", "") or "")
    category = str(faq.get("category", "") or "")
    return normalize_text(f"{question} {question} {answer} {category}")


# ============================================================
# CACHED INDEX
# ============================================================

@dataclass
class _Index:
    signature: str
    faqs: list
    norm_questions: list
    word_vec: TfidfVectorizer
    word_mat: object
    char_vec: TfidfVectorizer
    char_mat: object
    dense: Optional[np.ndarray] = None


_lock = threading.Lock()
_index: Optional[_Index] = None
_encoder = None
_encoder_failed = False
_reranker = None
_reranker_failed = False


def _get_encoder():
    global _encoder, _encoder_failed
    if not USE_DENSE or _encoder_failed:
        return None
    if _encoder is None:
        try:
            from sentence_transformers import SentenceTransformer

            _encoder = SentenceTransformer(EMBEDDING_MODEL)
        except Exception as e:
            log.warning("Dense retrieval disabled (%s); using sparse retrieval only.", e)
            _encoder_failed = True
            return None
    return _encoder


def _valid_faqs():
    faqs = list_faqs() or []
    return [f for f in faqs if isinstance(f, dict) and f.get("question") and f.get("answer")]


def _signature(faqs):
    h = hashlib.sha1()
    for f in faqs:
        h.update(
            f"{f.get('_id')}|{f['question']}|{f['answer']}|{f.get('category', '')}".encode("utf-8")
        )
    return h.hexdigest()


def _build_index(faqs, signature):
    corpus = [_prepare_faq_document(f) for f in faqs]

    word_vec = TfidfVectorizer(
        analyzer="word", ngram_range=(1, 2), sublinear_tf=True, strip_accents="unicode"
    )
    char_vec = TfidfVectorizer(
        analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True, strip_accents="unicode"
    )
    word_mat = word_vec.fit_transform(corpus)
    char_mat = char_vec.fit_transform(corpus)

    dense = None
    encoder = _get_encoder()
    if encoder is not None:
        dense = encoder.encode(
            [f"{f['question']}. {f['answer']}" for f in faqs],
            normalize_embeddings=True,
            show_progress_bar=False,
        )

    return _Index(
        signature=signature,
        faqs=faqs,
        norm_questions=[normalize_text(f["question"]) for f in faqs],
        word_vec=word_vec,
        word_mat=word_mat,
        char_vec=char_vec,
        char_mat=char_mat,
        dense=dense,
    )


def _get_index():
    """Return the cached index, rebuilding only if the FAQ collection changed."""
    global _index
    faqs = _valid_faqs()
    if not faqs:
        return None

    signature = _signature(faqs)
    with _lock:
        if _index is None or _index.signature != signature:
            log.info("Rebuilding retrieval index (%d FAQs)", len(faqs))
            _index = _build_index(faqs, signature)
        return _index


def invalidate_index():
    """Optional: call after an admin edits FAQs to force an immediate rebuild."""
    global _index
    with _lock:
        _index = None


# ============================================================
# RANK FUSION + RERANKING
# ============================================================

def _ranks(scores):
    """0-based rank of each item (0 = best)."""
    order = np.argsort(-np.asarray(scores))
    ranks = np.empty(len(order), dtype=int)
    ranks[order] = np.arange(len(order))
    return ranks


def _rerank(query, candidates):
    global _reranker, _reranker_failed
    if not USE_RERANKER or _reranker_failed or len(candidates) < 2:
        return candidates
    try:
        if _reranker is None:
            from sentence_transformers import CrossEncoder

            _reranker = CrossEncoder(RERANK_MODEL)
        scores = _reranker.predict(
            [(query, f"{c['question']}. {c['answer']}") for c in candidates]
        )
    except Exception as e:
        log.warning("Reranker disabled (%s).", e)
        _reranker_failed = True
        return candidates

    for c, s in zip(candidates, scores):
        c["rerank_score"] = round(float(s), 4)
    return sorted(candidates, key=lambda c: c["rerank_score"], reverse=True)


# ============================================================
# PUBLIC API
# ============================================================

def retrieve_relevant_faqs(
    query: str,
    top_k=DEFAULT_TOP_K,
    min_score=DEFAULT_MIN_SCORE,
    use_dense=True,
):
    """
    Returns a list of dicts:
      id, question, answer, category, score (fused, 0-1),
      lexical_score, dense_score, retrieval_method
    Returns [] when nothing is sufficiently relevant.

    `use_dense=False` gives the sparse-only baseline (used by the eval harness).
    """

    if not isinstance(query, str) or not query.strip():
        return []

    try:
        top_k = max(1, min(int(top_k), 10))
        min_score = max(0.0, min(float(min_score), 1.0))
    except (TypeError, ValueError):
        top_k, min_score = DEFAULT_TOP_K, DEFAULT_MIN_SCORE

    index = _get_index()
    if index is None:
        return []

    q_norm = normalize_text(query)
    q_expanded = expand_query(query)
    if not q_norm:
        return []

    n = len(index.faqs)

    # --- Sparse signals -------------------------------------------------
    word_scores = cosine_similarity(index.word_vec.transform([q_expanded]), index.word_mat).ravel()
    char_scores = cosine_similarity(index.char_vec.transform([q_norm]), index.char_mat).ravel()
    lexical = WORD_WEIGHT * word_scores + CHAR_WEIGHT * char_scores

    for i, question in enumerate(index.norm_questions):
        if q_norm in question:  # exact phrase bonus
            lexical[i] = min(1.0, lexical[i] + 0.15)

    # --- Dense signal ---------------------------------------------------
    dense_scores = None
    if use_dense and index.dense is not None:
        encoder = _get_encoder()
        if encoder is not None:
            q_vec = encoder.encode([query], normalize_embeddings=True, show_progress_bar=False)[0]
            dense_scores = index.dense @ q_vec

    # --- Reciprocal Rank Fusion ----------------------------------------
    signals = [(LEXICAL_RRF_WEIGHT, lexical)]
    if dense_scores is not None:
        signals.append((DENSE_RRF_WEIGHT, dense_scores))

    fused = np.zeros(n)
    for weight, scores in signals:
        fused += weight / (RRF_K + _ranks(scores) + 1)
    fused /= sum(w for w, _ in signals) / (RRF_K + 1)  # normalise to 0-1

    # --- Relevance gating + candidate assembly --------------------------
    method = "hybrid_rrf" if dense_scores is not None else "hybrid_tfidf"
    limit = max(top_k, RERANK_CANDIDATES)
    candidates = []

    for i in np.argsort(-fused):
        lexical_gate = LEXICAL_GATE_WITH_DENSE if dense_scores is not None else min_score
        lexical_ok = lexical[i] >= max(lexical_gate, min_score)
        dense_ok = dense_scores is not None and dense_scores[i] >= MIN_DENSE_SCORE
        if not (lexical_ok or dense_ok):
            continue

        faq = index.faqs[i]
        candidates.append(
            {
                "id": str(faq.get("_id", "")),
                "question": faq["question"],
                "answer": faq["answer"],
                "category": faq.get("category", "general"),
                "score": round(float(fused[i]), 4),
                "lexical_score": round(float(lexical[i]), 4),
                "dense_score": round(float(dense_scores[i]), 4) if dense_scores is not None else None,
                "retrieval_method": method,
            }
        )
        if len(candidates) >= limit:
            break

    return _rerank(query, candidates)[:top_k]