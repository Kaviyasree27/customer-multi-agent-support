import logging
import re
from concurrent.futures import ThreadPoolExecutor

from agents import query_agent, order_agent, complaint_agent, sentiment_agent
from agents.base_agent import AgentResult, LLMUnavailableError
from models import conversation_model, ticket_model, order_model

log = logging.getLogger("aria.orchestrator")

# Which physical agent gets triggered per detected intent.
INTENT_ROUTES = {
    "order_status": "order_agent",
    "order_cancel": "order_agent",
    "complaint": "complaint_agent",
    "ticket_status": "complaint_agent",
    "faq_question": "query_agent",
    "greeting": "query_agent",
    "human_handoff": "handoff",
    "other": "query_agent",
}

CONFIRM_RE = re.compile(
    r"^\s*(yes|y|yeah|yep|yup|confirm|confirmed|go ahead|proceed|sure|ok|okay|please do)\b", re.I
)
DECLINE_RE = re.compile(
    r"^\s*(no|n|nope|nah|don'?t|do not|stop|never ?mind|keep it)\b", re.I
)

# Sentiment analysis runs concurrently with intent detection.
_pool = ThreadPoolExecutor(max_workers=4)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _format_history(msgs) -> str:
    lines = []
    for m in msgs:
        speaker = "Customer" if m["role"] == "user" else "Agent"
        lines.append(f"{speaker}: {m['content']}")
    return "\n".join(lines) if lines else "(no prior messages)"


def _pending_cancellation(msgs):
    """Order number awaiting a yes/no, if the last agent turn asked to confirm a cancellation."""
    for m in reversed(msgs):
        if m.get("role") == "user":
            continue
        return (m.get("meta") or {}).get("pending_cancellation")
    return None


def _grounded_id(value, *texts):
    """Keep an LLM-extracted identifier only if it literally appears in the conversation."""
    if not value:
        return None
    needle = re.sub(r"\s+", "", value).lower()
    haystack = re.sub(r"\s+", "", " ".join(texts)).lower()
    return value if needle and needle in haystack else None


def _order_db_id(customer_id, order_number):
    if not order_number:
        return None
    order = order_model.find_order_by_number(order_number, customer_id=customer_id)
    return order["_id"] if order else None


def _latest_open_ticket_for_customer(customer_id: str):
    tickets = ticket_model.list_tickets_for_customer(customer_id)
    open_ones = [t for t in tickets if t["status"] not in ("resolved", "closed")]
    return open_ones[0] if open_ones else None


def _escalate_conversation_ticket(conversation_id, customer_id, reason):
    """On human handoff make sure there is a ticket an admin can act on."""
    open_ticket = _latest_open_ticket_for_customer(customer_id)
    if open_ticket:
        ticket_model.escalate_ticket(open_ticket["_id"], reason)
    else:
        ticket = ticket_model.create_ticket(
            customer_id=customer_id,
            subject="Human agent requested",
            description=f"Customer requested human handoff in conversation {conversation_id}.",
            category="service_quality",
            priority="high",
            source="chat",
        )
        ticket_model.escalate_ticket(ticket["_id"], reason)


def _create_complaint(customer_id, message, history_text, order_number, sentiment):
    result = complaint_agent.create_ticket_from_message(
        customer_id,
        message,
        history_text,
        order_id=_order_db_id(customer_id, order_number),
    )
    ticket_id = result.data.pop("ticket_id", None)  # internal only, never sent to the client
    if ticket_id and sentiment_agent.maybe_escalate(ticket_id, sentiment):
        result.actions.append("escalated")
    return result


def _failure(conversation_id, customer_id, reply):
    conversation_model.add_message(
        conversation_id, customer_id, "agent", reply, meta={"agent": "system", "error": True}
    )
    return {
        "conversation_id": conversation_id,
        "reply": reply,
        "agent": "system",
        "intent": None,
        "sentiment": None,
        "actions": [],
        "data": {},
    }


# ------------------------------------------------------------------
# Main entry point
# ------------------------------------------------------------------

def handle_message(customer_id: str, message: str, conversation_id: str = None) -> dict:
    convo = conversation_model.get_or_create_conversation(customer_id, conversation_id)
    conversation_id = convo["_id"]

    conversation_model.add_message(conversation_id, customer_id, "user", message)
    msgs = conversation_model.get_history(conversation_id, limit=12)
    history_text = _format_history(msgs)
    pending = _pending_cancellation(msgs)

    try:
        return _run_turn(customer_id, message, conversation_id, history_text, pending)
    except LLMUnavailableError as e:
        return _failure(conversation_id, customer_id, str(e))
    except Exception:
        log.exception("Unhandled error while processing chat turn")
        return _failure(
            conversation_id,
            customer_id,
            "Sorry, something went wrong on our side. Please try again, "
            "or ask me to connect you with a human agent.",
        )


def _run_turn(customer_id, message, conversation_id, history_text, pending) -> dict:
    # Sentiment/urgency runs in parallel with intent detection (latency: max, not sum).
    sentiment_future = _pool.submit(sentiment_agent.analyze, message, history_text)

    resolving_pending = bool(pending) and bool(CONFIRM_RE.match(message) or DECLINE_RE.match(message))
    secondary = []

    if resolving_pending:
        intent, order_number, ticket_number = "order_cancel", pending, None
    else:
        intent_result = query_agent.detect_intent(message, history_text)
        intent = intent_result.get("intent", "other")
        secondary = intent_result.get("secondary_intents", [])
        # Guardrail: extracted identifiers must literally appear in the conversation.
        order_number = _grounded_id(intent_result.get("order_number"), message, history_text)
        ticket_number = _grounded_id(intent_result.get("ticket_number"), message, history_text)

    sentiment = sentiment_future.result()
    route = INTENT_ROUTES.get(intent, "query_agent")

    if resolving_pending:
        if CONFIRM_RE.match(message):
            result = order_agent.handle_cancellation(customer_id, message, order_number, confirmed=True)
        else:
            result = AgentResult(
                reply=f"No problem, I've left order {order_number} as it is.",
                agent="order_agent",
                actions=["cancellation_declined"],
            )

    elif route == "handoff":
        conversation_model.touch_conversation(conversation_id, status="escalated", last_intent=intent)
        result = AgentResult(
            reply="I'm connecting you with a human support agent now. Someone from our team "
                  "will pick this up shortly. You can keep describing the issue here in the "
                  "meantime and they'll see full context.",
            agent="handoff",
            actions=["human_handoff_requested"],
        )
        _escalate_conversation_ticket(
            conversation_id, customer_id, "Customer explicitly requested a human agent"
        )

    elif route == "order_agent":
        if intent == "order_cancel":
            result = order_agent.handle_cancellation(customer_id, message, order_number)
        else:
            result = order_agent.handle_order_status(customer_id, message, order_number)

    elif route == "complaint_agent":
        if intent == "ticket_status":
            result = complaint_agent.check_ticket_status(customer_id, message, ticket_number)
        else:
            result = _create_complaint(customer_id, message, history_text, order_number, sentiment)

    else:
        result = query_agent.answer_with_rag(message, history_text)

    # Multi-intent: e.g. "cancel my order and file a complaint about the delay".
    if (
        "complaint" in secondary
        and intent in ("order_status", "order_cancel", "faq_question")
        and not resolving_pending
    ):
        extra = _create_complaint(customer_id, message, history_text, order_number, sentiment)
        result.reply = f"{result.reply}\n\n{extra.reply}"
        result.actions += extra.actions
        result.data["ticket"] = extra.data.get("ticket")

    # Mid-conversation escalation: sentiment runs every turn.
    if (
        route != "handoff"
        and sentiment.get("is_frustrated")
        and sentiment.get("urgency") in ("high", "critical")
    ):
        open_ticket = _latest_open_ticket_for_customer(customer_id)
        if open_ticket and not open_ticket.get("escalated"):
            ticket_model.escalate_ticket(open_ticket["_id"], sentiment.get("reason", "High urgency detected"))
            if "escalated" not in result.actions:
                result.actions.append("escalated")

    conversation_model.add_message(
        conversation_id,
        customer_id,
        "agent",
        result.reply,
        meta={
            "agent": result.agent,
            "actions": result.actions,
            "sentiment": sentiment,
            "pending_cancellation": result.data.get("pending_cancellation"),
        },
    )
    conversation_model.touch_conversation(
        conversation_id, last_intent=intent, last_sentiment=sentiment.get("sentiment_score")
    )

    return {
        "conversation_id": conversation_id,
        "reply": result.reply,
        "agent": result.agent,
        "intent": intent,
        "sentiment": sentiment,
        "actions": result.actions,
        "data": result.data,
    }