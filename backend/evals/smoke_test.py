"""
End-to-end smoke test for Aria: sends realistic customer messages through the
real orchestrator (LLM + MongoDB) and checks that the right agent and action fired.

Run from backend/:
    python -m evals.smoke_test
    python -m evals.smoke_test --customer-id <mongo user id>   # if the demo user isn't found

Side effects on the demo customer: a few chat conversations are created and one
support ticket may be created or escalated. No order is cancelled (the
cancellation test answers "no" to the confirmation).
"""

import sys
import time
from datetime import datetime, timezone

from agents import orchestrator
from models import order_model

DEMO_EMAIL = "demo@customer.local"


def _has(result, action):
    return action in (result.get("actions") or [])


def _find_customer_id(db):
    if "--customer-id" in sys.argv:
        return sys.argv[sys.argv.index("--customer-id") + 1]
    user = db.users.find_one({"email": DEMO_EMAIL})
    return str(user["_id"]) if user else None


def build_cases(customer_id):
    orders = order_model.list_orders_for_customer(customer_id)
    any_order = orders[0]["order_number"] if orders else None
    cancellable = next(
        (o["order_number"] for o in orders if order_model.is_cancellable(o)[0]), None
    )

    return [
        {
            "name": "greeting",
            "messages": ["hi there"],
            "check": lambda r: (r["agent"] == "query_agent", "query_agent handles greeting"),
        },
        {
            "name": "faq_answer (RAG)",
            "messages": ["How long does shipping take?"],
            "check": lambda r: (
                r["agent"] == "query_agent" and _has(r, "faq_answer_generated"),
                "query_agent + faq_answer_generated",
            ),
        },
        {
            "name": "faq_out_of_scope",
            "messages": ["Do you sell gift cards?"],
            "check": lambda r: (
                r["agent"] == "query_agent" and _has(r, "knowledge_base_no_match"),
                "query_agent + knowledge_base_no_match (no invented answer)",
            ),
        },
        {
            "name": "order_status",
            "messages": [f"Where is my order {any_order}?"] if any_order else [],
            "skip": "no orders for this customer" if not any_order else None,
            "check": lambda r: (
                r["agent"] == "order_agent" and bool(r["data"].get("orders")),
                "order_agent + real order data",
            ),
        },
        {
            "name": "cancel_asks_confirmation",
            "messages": [f"Please cancel order {cancellable}"] if cancellable else [],
            "skip": "no cancellable order for this customer" if not cancellable else None,
            "check": lambda r: (
                _has(r, "cancellation_confirmation_requested"),
                "cancellation_confirmation_requested",
            ),
        },
        {
            "name": "cancel_decline_flow (multi-turn)",
            "messages": [f"Please cancel order {cancellable}", "no"] if cancellable else [],
            "skip": "no cancellable order for this customer" if not cancellable else None,
            "check": lambda r: (
                _has(r, "cancellation_declined"),
                "cancellation_declined (confirmation state remembered between turns)",
            ),
        },
        {
            "name": "complaint_creates_ticket",
            "messages": ["My package arrived damaged and I want to file a complaint"],
            "check": lambda r: (
                r["agent"] == "complaint_agent"
                and (_has(r, "ticket_created") or _has(r, "duplicate_ticket_avoided")),
                "complaint_agent + ticket_created (or duplicate avoided)",
            ),
        },
        {
            "name": "ticket_status",
            "messages": ["Can you show me the status of my tickets?"],
            "check": lambda r: (
                r["agent"] == "complaint_agent" and "tickets" in r["data"],
                "complaint_agent + ticket list",
            ),
        },
        {
            "name": "sentiment_frustrated",
            "messages": ["This is unacceptable! Third time my order is late and nobody helps. "
                         "I am furious, fix it right now!"],
            "check": lambda r: (
                bool(r.get("sentiment")) and bool(r["sentiment"].get("is_frustrated")),
                "sentiment agent flags is_frustrated",
            ),
        },
        {
            "name": "human_handoff",
            "messages": ["I want to talk to a real human agent"],
            "check": lambda r: (
                r["agent"] == "handoff" and _has(r, "human_handoff_requested"),
                "handoff + human_handoff_requested",
            ),
        },
    ]


def run_case(customer_id, case):
    conversation_id, result = None, None
    started = time.perf_counter()
    for message in case["messages"]:
        result = orchestrator.handle_message(customer_id, message, conversation_id)
        conversation_id = result["conversation_id"]
    elapsed = time.perf_counter() - started
    passed, expectation = case["check"](result)
    return passed, expectation, result, elapsed


def _safe(text, limit=110):
    return (text or "").replace("\n", " ")[:limit].encode("ascii", "replace").decode()


def main():
    from extensions import db

    started_at = datetime.now(timezone.utc)
    customer_id = _find_customer_id(db)
    if not customer_id:
        print(f"Demo customer {DEMO_EMAIL} not found. Run seed.py or pass --customer-id.")
        sys.exit(1)

    failures = 0
    print(f"\nRunning smoke test for customer {customer_id}\n")

    for case in build_cases(customer_id):
        if case.get("skip"):
            print(f"SKIP  {case['name']:<34} ({case['skip']})")
            continue
        try:
            passed, expectation, result, elapsed = run_case(customer_id, case)
        except Exception as e:  # a crash is a failure, not the end of the run
            failures += 1
            print(f"FAIL  {case['name']:<34} crashed: {type(e).__name__}: {e}")
            continue

        status = "PASS" if passed else "FAIL"
        failures += not passed
        print(f"{status}  {case['name']:<34} agent={result['agent']:<16} "
              f"intent={result['intent']!s:<14} {elapsed:4.1f}s")
        print(f"      reply: {_safe(result['reply'])}")
        if not passed:
            print(f"      expected: {expectation}")
            print(f"      got actions={result['actions']}")

    print("\nLLM telemetry for this run (collection: llm_calls)")
    for status in ("ok", "retry", "error"):
        count = db.llm_calls.count_documents(
            {"created_at": {"$gte": started_at}, "status": status}
        )
        print(f"  {status:<6}: {count}")

    print(f"\n{'ALL CHECKS PASSED' if not failures else f'{failures} CHECK(S) FAILED'}")
    sys.exit(1 if failures else 0)


def _run():
    try:
        from app import create_app
    except ImportError:
        return main()
    with create_app().app_context():
        main()


if __name__ == "__main__":
    _run()