
from agents.base_agent import call_llm_json, AgentResult
from models import ticket_model


VALID_CATEGORIES = {
    "product_defect",
    "delivery_delay",
    "billing",
    "wrong_item",
    "refund",
    "account",
    "service_quality",
    "other",
}

VALID_PRIORITIES = {"low", "medium", "high", "critical"}


CLASSIFY_PROMPT = """You triage customer complaints for an e-commerce support system.

Analyze the customer's issue and return:
- subject: short subject, maximum 8 words
- category: exactly one of product_defect, delivery_delay, billing,
  wrong_item, refund, account, service_quality, other
- priority: exactly one of low, medium, high, critical
- description: clear 1-3 sentence summary of the reported issue

Priority guidance:
- critical: immediate safety risk, serious harm, or severe urgent impact
- high: major product defect, significant financial issue, or urgent disruption
- medium: ordinary complaint requiring support action
- low: minor issue, suggestion, or non-urgent concern

Do not invent facts. Return valid JSON with exactly these keys:
subject, category, priority, description.
"""


def create_ticket_from_message(
    customer_id: str,
    message: str,
    history_text: str,
    order_id: str = None,
) -> AgentResult:

    prompt = (
        f"Conversation history:\n{history_text}\n\n"
        f"Customer's latest message:\n{message}"
    )

    classification = call_llm_json(CLASSIFY_PROMPT, prompt) or {}

    subject = str(classification.get("subject") or "Customer complaint").strip()
    category = str(classification.get("category") or "other").strip().lower()
    priority = str(classification.get("priority") or "medium").strip().lower()
    description = str(classification.get("description") or message).strip()

    # Validate model-generated fields before saving them.
    if category not in VALID_CATEGORIES:
        category = "other"

    if priority not in VALID_PRIORITIES:
        priority = "medium"

    if not subject:
        subject = "Customer complaint"

    if not description:
        description = message

    ticket = ticket_model.create_ticket(
        customer_id=customer_id,
        subject=subject,
        description=description,
        category=category,
        priority=priority,
        source="chat",
        order_id=order_id,
    )

    # Deterministic response: only confirmed ticket data is stated.
    reply = (
        "I'm sorry you're experiencing this issue. "
        "I've created a support ticket for you.\n\n"
        f"Ticket Number: {ticket['ticket_number']}\n"
        f"Priority: {ticket['priority'].capitalize()}\n"
        f"Status: {ticket['status'].replace('_', ' ').capitalize()}\n\n"
        "Our support team can review the details using this ticket number. "
        "Please keep it for reference. I haven't confirmed a replacement, "
        "refund, or response timeframe."
    )

    return AgentResult(
        reply=reply,
        agent="complaint_agent",
        data={"ticket": _public(ticket)},
        actions=["ticket_created"],
    )


def check_ticket_status(
    customer_id: str,
    message: str,
    ticket_number: str = None,
) -> AgentResult:

    customer_tickets = ticket_model.list_tickets_for_customer(customer_id)

    if ticket_number:
        tickets = [
            t for t in customer_tickets
            if t["ticket_number"].lower() == ticket_number.strip().lower()
        ]
    else:
        tickets = customer_tickets[:5]

    if not tickets:
        return AgentResult(
            reply=(
                "I couldn't find a matching ticket on your account. "
                "Please check the ticket number and try again."
            ),
            agent="complaint_agent",
            data={"tickets": []},
        )

    if ticket_number:
        ticket = tickets[0]
        reply = (
            f"Here is the latest status for ticket {ticket['ticket_number']}:\n\n"
            f"Issue: {ticket['subject']}\n"
            f"Status: {ticket['status'].replace('_', ' ').capitalize()}\n"
            f"Priority: {ticket['priority'].capitalize()}\n\n"
            "This status is based on the ticket record currently available."
        )
    else:
        lines = [
            f"- {t['ticket_number']}: {t['subject']} | "
            f"Status: {t['status'].replace('_', ' ').capitalize()} | "
            f"Priority: {t['priority'].capitalize()}"
            for t in tickets
        ]

        reply = "Here are your recent support tickets:\n\n" + "\n".join(lines)

    return AgentResult(
        reply=reply,
        agent="complaint_agent",
        data={"tickets": [_public(t) for t in tickets]},
    )


def _public(ticket: dict) -> dict:
    return {
        "ticket_number": ticket["ticket_number"],
        "subject": ticket["subject"],
        "category": ticket["category"],
        "priority": ticket["priority"],
        "status": ticket["status"],
        "escalated": ticket.get("escalated", False),
    }
