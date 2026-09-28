from agents import query_agent, order_agent, complaint_agent, sentiment_agent
from agents.base_agent import AgentResult, LLMUnavailableError
from models import conversation_model, ticket_model

# Which physical agent(s) get triggered per detected intent.
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


def _history_text(conversation_id: str) -> str:
    msgs = conversation_model.get_history(conversation_id, limit=12)
    lines = []
    for m in msgs:
        speaker = "Customer" if m["role"] == "user" else "Agent"
        lines.append(f"{speaker}: {m['content']}")
    return "\n".join(lines) if lines else "(no prior messages)"


def handle_message(customer_id: str, message: str, conversation_id: str = None) -> dict:
    convo = conversation_model.get_or_create_conversation(customer_id, conversation_id)
    conversation_id = convo["_id"]

    conversation_model.add_message(conversation_id, customer_id, "user", message)
    history_text = _history_text(conversation_id)

    try:
        intent_result = query_agent.detect_intent(message, history_text)
        sentiment = sentiment_agent.analyze(message, history_text)
    except LLMUnavailableError as e:
        reply = str(e)
        conversation_model.add_message(conversation_id, customer_id, "agent", reply,
                                        meta={"agent": "system", "error": True})
        return {
            "conversation_id": conversation_id,
            "reply": reply,
            "agent": "system",
            "intent": None,
            "sentiment": None,
            "actions": [],
            "data": {},
        }

    intent = intent_result.get("intent", "other")
    order_number = intent_result.get("order_number")
    ticket_number = intent_result.get("ticket_number")

    route = INTENT_ROUTES.get(intent, "query_agent")

    if route == "handoff":
        conversation_model.touch_conversation(conversation_id, status="escalated", last_intent=intent)
        result = AgentResult(
            reply="I'm connecting you with a human support agent now. Someone from our team "
                  "will pick this up shortly — you can keep describing the issue here in the "
                  "meantime and they'll see full context.",
            agent="handoff",
            actions=["human_handoff_requested"],
        )
        _escalate_conversation_ticket(conversation_id, customer_id, "Customer explicitly requested a human agent")
    elif route == "order_agent":
        if intent == "order_cancel":
            result = order_agent.handle_cancellation(customer_id, message, order_number)
        else:
            result = order_agent.handle_order_status(customer_id, message, order_number)
    elif route == "complaint_agent":
        if intent == "ticket_status":
            result = complaint_agent.check_ticket_status(customer_id, message, ticket_number)
        else:
            result = complaint_agent.create_ticket_from_message(customer_id, message, history_text)
            ticket = result.data.get("ticket")
            if ticket:
                esc_reason = sentiment_agent.maybe_escalate(
                    _ticket_db_id(ticket["ticket_number"]), sentiment
                )
                if esc_reason:
                    result.actions.append("escalated")
    else:
        result = query_agent.answer_with_rag(message, history_text)

    # Sentiment agent runs on every turn; if the conversation already has an open ticket
    # and sentiment/urgency spikes mid-conversation, escalate that ticket too.
    if route != "handoff" and sentiment.get("is_frustrated") and sentiment.get("urgency") in ("high", "critical"):
        open_ticket = _latest_open_ticket_for_customer(customer_id)
        if open_ticket and not open_ticket.get("escalated"):
            ticket_model.escalate_ticket(open_ticket["_id"], sentiment.get("reason", "High urgency detected"))
            result.actions.append("escalated")

    conversation_model.add_message(
        conversation_id, customer_id, "agent", result.reply,
        meta={"agent": result.agent, "actions": result.actions, "sentiment": sentiment},
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


def _ticket_db_id(ticket_number: str):
    t = None
    from extensions import db
    t = db.tickets.find_one({"ticket_number": ticket_number})
    return t["_id"] if t else None


def _latest_open_ticket_for_customer(customer_id: str):
    tickets = ticket_model.list_tickets_for_customer(customer_id)
    open_ones = [t for t in tickets if t["status"] not in ("resolved", "closed")]
    return open_ones[0] if open_ones else None


def _escalate_conversation_ticket(conversation_id, customer_id, reason):
    """When a human handoff is requested, make sure there's a ticket an admin can see
    and act on -- create one tied to this conversation if none is open."""
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
