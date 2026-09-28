"""
Offline evaluation harness for Aria.

Run from backend/ (with .env configured and FAQs seeded):
    python -m evals.run_eval

Reports:
  - intent classification accuracy + mean latency
  - order-number extraction accuracy
  - retrieval hit@3 and MRR for the sparse (TF-IDF) baseline vs the hybrid
    (sparse + dense, RRF) retriever

Case format (evals/cases.jsonl, one JSON object per line):
  {"message": "...", "expected_intent": "order_cancel", "expected_order_number": "ORD-1002"}
  {"message": "...", "expected_faq": "substring of the FAQ question that should be retrieved"}
"""

import json
import time
from pathlib import Path

from agents import query_agent
from agents.knowledge_base import retrieve_relevant_faqs

CASES = Path(__file__).with_name("cases.jsonl")


def load_cases():
    lines = CASES.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def eval_intent(cases):
    rows = [c for c in cases if "expected_intent" in c]
    correct = id_total = id_ok = 0
    latencies = []

    for c in rows:
        started = time.perf_counter()
        out = query_agent.detect_intent(c["message"], c.get("history", "(no prior messages)"))
        latencies.append(time.perf_counter() - started)

        correct += out["intent"] == c["expected_intent"]
        if "expected_order_number" in c:
            id_total += 1
            id_ok += (out["order_number"] or "").lower() == c["expected_order_number"].lower()

    n = max(len(rows), 1)
    return {
        "cases": len(rows),
        "intent_accuracy": correct / n,
        "order_id_accuracy": (id_ok / id_total) if id_total else None,
        "mean_latency_s": sum(latencies) / n,
    }


def eval_retrieval(cases, use_dense, k=3):
    rows = [c for c in cases if "expected_faq" in c]
    hits = 0
    reciprocal_rank = 0.0

    for c in rows:
        results = retrieve_relevant_faqs(c["message"], top_k=k, use_dense=use_dense)
        ranks = [
            i for i, r in enumerate(results, start=1)
            if c["expected_faq"].lower() in r["question"].lower()
        ]
        if ranks:
            hits += 1
            reciprocal_rank += 1 / ranks[0]

    n = max(len(rows), 1)
    return {"cases": len(rows), f"hit@{k}": hits / n, "mrr": reciprocal_rank / n}


def main():
    cases = load_cases()

    print("\n== Intent classification ==")
    for key, value in eval_intent(cases).items():
        print(f"{key:>20}: {value if not isinstance(value, float) else round(value, 3)}")

    print("\n== Retrieval ==")
    for label, use_dense in (("sparse baseline", False), ("hybrid (RRF)", True)):
        result = eval_retrieval(cases, use_dense)
        print(f"{label:>16}: " + ", ".join(f"{k}={round(v, 3) if isinstance(v, float) else v}" for k, v in result.items()))


def _run():
    try:
        from app import create_app
    except ImportError:
        return main()
    with create_app().app_context():
        main()


if __name__ == "__main__":
    _run()