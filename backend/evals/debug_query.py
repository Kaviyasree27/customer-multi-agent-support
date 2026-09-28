"""
Shows exactly what happens to a customer message, step by step:
  1) which intent was detected and which agent it routes to
  2) what the FAQ search returned (with scores)
  3) the FAQ answer the bot would give

Run from backend/:
    python -m evals.debug_query "what is the refund" "when will it be returned"
With no arguments it tests a few refund/return questions.
"""

import sys

from agents import query_agent
from agents.knowledge_base import retrieve_relevant_faqs
from agents.orchestrator import INTENT_ROUTES

DEFAULTS = [
    "what is the refund",
    "when will i get my refund",
    "when will it be returned",
    "what is your refund policy",
]


def show(message):
    print("\n" + "=" * 70)
    print("Message:", message)

    intent = query_agent.detect_intent(message, "(no prior messages)")
    route = INTENT_ROUTES.get(intent["intent"], "query_agent")
    print(f"\n1) Intent: {intent['intent']}  ->  handled by: {route}")
    if route != "query_agent" and route != "greeting":
        print("   NOTE: this never reaches the FAQ search. The intent was routed elsewhere.")

    print("\n2) FAQ search (top 3):")
    results = retrieve_relevant_faqs(message, top_k=3)
    if not results:
        print("   NO RESULTS -> the bot will say it couldn't find an answer")
    for r in results:
        print(f"   - {r['question']}   lexical={r['lexical_score']}  dense={r['dense_score']}")

    print("\n3) FAQ answer:")
    out = query_agent.answer_with_rag(message, "(no prior messages)")
    print("  ", out.reply.replace("\n", " "))
    print("   actions:", out.actions)


def main():
    for message in (sys.argv[1:] or DEFAULTS):
        show(message)


def _run():
    try:
        from app import create_app
    except ImportError:
        return main()
    with create_app().app_context():
        main()


if __name__ == "__main__":
    _run()