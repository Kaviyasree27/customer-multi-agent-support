
"""
Aria Support - Hybrid FAQ Retrieval Engine

Retrieval methods:
1. Word-level TF-IDF
2. Phrase matching
3. Character n-gram similarity
4. Query normalization and synonym expansion

Uses local scikit-learn only.
No paid API or external embedding service required.
"""

import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from models.feedback_model import list_faqs


# ============================================================
# CONFIGURATION
# ============================================================

DEFAULT_TOP_K = 3
DEFAULT_MIN_SCORE = 0.12

WORD_WEIGHT = 0.65
CHAR_WEIGHT = 0.35


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
    """
    Normalize text for consistent retrieval.
    """

    if not isinstance(text, str):
        return ""

    text = text.lower().strip()

    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text


def expand_query(query):
    """
    Expand common customer-support terms.

    Example:
    'My laptop is broken'

    becomes:
    'my laptop is broken damaged defective cracked'
    """

    normalized = normalize_text(query)

    if not normalized:
        return ""

    expanded_terms = [normalized]

    words = set(normalized.split())

    for word in words:
        if word in SYNONYMS:
            expanded_terms.extend(SYNONYMS[word])

        for key, alternatives in SYNONYMS.items():
            if word in alternatives:
                expanded_terms.append(key)

    return " ".join(expanded_terms)


# ============================================================
# FAQ DOCUMENT PREPARATION
# ============================================================

def _prepare_faq_document(faq):
    """
    Convert a MongoDB FAQ document into searchable text.
    """

    question = str(faq.get("question", "") or "")
    answer = str(faq.get("answer", "") or "")
    category = str(faq.get("category", "") or "")

    return normalize_text(
        f"{question} {question} {answer} {category}"
    )


# ============================================================
# HYBRID RETRIEVAL
# ============================================================

def retrieve_relevant_faqs(
    query: str,
    top_k=DEFAULT_TOP_K,
    min_score=DEFAULT_MIN_SCORE,
):
    """
    Retrieve relevant FAQ documents from MongoDB.

    Returns:
        [
            {
                "question": "...",
                "answer": "...",
                "score": 0.85,
                "category": "returns"
            }
        ]

    Returns [] if no sufficiently relevant FAQ is found.
    """

    if not isinstance(query, str) or not query.strip():
        return []

    try:
        top_k = max(1, min(int(top_k), 10))
        min_score = max(0.0, min(float(min_score), 1.0))
    except (TypeError, ValueError):
        top_k = DEFAULT_TOP_K
        min_score = DEFAULT_MIN_SCORE

    # Step 1: Load FAQs dynamically from MongoDB.

    faqs = list_faqs()

    if not faqs:
        return []

    valid_faqs = []

    for faq in faqs:
        if not isinstance(faq, dict):
            continue

        question = faq.get("question")
        answer = faq.get("answer")

        if not question or not answer:
            continue

        valid_faqs.append(faq)

    if not valid_faqs:
        return []

    # Step 2: Prepare documents.

    corpus = [
        _prepare_faq_document(faq)
        for faq in valid_faqs
    ]

    expanded_query = expand_query(query)

    if not expanded_query:
        return []

    # Step 3: Word-level TF-IDF.
    # Captures matching words and short phrases.

    try:
        word_vectorizer = TfidfVectorizer(
            analyzer="word",
            ngram_range=(1, 2),
            sublinear_tf=True,
            strip_accents="unicode",
        )

        word_matrix = word_vectorizer.fit_transform(corpus)

        query_vector = word_vectorizer.transform(
            [expanded_query]
        )

        word_scores = cosine_similarity(
            query_vector,
            word_matrix
        ).flatten()

    except ValueError:
        word_scores = [0.0] * len(valid_faqs)

    # Step 4: Character-level TF-IDF.
    # Helps match related word forms and minor spelling variations.

    try:
        char_vectorizer = TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(3, 5),
            sublinear_tf=True,
            strip_accents="unicode",
        )

        char_matrix = char_vectorizer.fit_transform(corpus)

        char_query_vector = char_vectorizer.transform(
            [normalize_text(query)]
        )

        char_scores = cosine_similarity(
            char_query_vector,
            char_matrix
        ).flatten()

    except ValueError:
        char_scores = [0.0] * len(valid_faqs)

    # Step 5: Combine scores.

    ranked_results = []

    for index, faq in enumerate(valid_faqs):

        word_score = float(word_scores[index])
        char_score = float(char_scores[index])

        combined_score = (
            WORD_WEIGHT * word_score
            + CHAR_WEIGHT * char_score
        )

        # Small bonus for exact question phrase matches.
        normalized_question = normalize_text(
            faq.get("question", "")
        )

        normalized_query = normalize_text(query)

        if (
            normalized_query
            and normalized_query in normalized_question
        ):
            combined_score = min(
                1.0,
                combined_score + 0.15
            )

        if combined_score < min_score:
            continue

        ranked_results.append({
            "question": faq["question"],
            "answer": faq["answer"],
            "category": faq.get("category", "general"),
            "score": round(combined_score, 4),
            "retrieval_method": "hybrid_tfidf",
        })

    # Step 6: Return highest-scoring FAQs.

    ranked_results.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    return ranked_results[:top_k]
