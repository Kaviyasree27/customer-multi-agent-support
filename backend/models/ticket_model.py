from extensions import db
from utils.helpers import new_id, now, ticket_number


def create_ticket(customer_id, subject, description, category="general",
                   priority="medium", source="chat", order_id=None):
    ticket = {
        "_id": new_id(),
        "ticket_number": ticket_number(),
        "customer_id": customer_id,
        "subject": subject,
        "description": description,
        "category": category,
        "priority": priority,  # low | medium | high | critical
        "status": "open",  # open -> in_progress -> resolved -> closed ; or escalated
        "source": source,  # chat | manual
        "order_id": order_id,
        "escalated": False,
        "escalation_reason": None,
        "assigned_to": None,
        "created_at": now(),
        "updated_at": now(),
        "resolution": None,
        "activity": [{"event": "created", "at": now().isoformat(), "by": "system"}],
    }
    db.tickets.insert_one(ticket)
    return ticket


def find_ticket(ticket_id):
    return db.tickets.find_one({"_id": ticket_id})


def list_tickets_for_customer(customer_id):
    return list(db.tickets.find({"customer_id": customer_id}).sort("created_at", -1))


def list_all_tickets(status=None, priority=None, escalated=None, limit=300):
    query = {}
    if status:
        query["status"] = status
    if priority:
        query["priority"] = priority
    if escalated is not None:
        query["escalated"] = escalated
    return list(db.tickets.find(query).sort("created_at", -1).limit(limit))


def update_ticket(ticket_id, updates: dict, activity_event=None):
    updates["updated_at"] = now()
    op = {"$set": updates}
    if activity_event:
        op["$push"] = {"activity": {"event": activity_event, "at": now().isoformat(), "by": "admin"}}
    db.tickets.update_one({"_id": ticket_id}, op)
    return find_ticket(ticket_id)


def escalate_ticket(ticket_id, reason):
    return update_ticket(
        ticket_id,
        {"escalated": True, "escalation_reason": reason, "priority": "critical", "status": "escalated"},
        activity_event=f"auto-escalated: {reason}",
    )


def resolve_ticket(ticket_id, resolution):
    return update_ticket(
        ticket_id,
        {"status": "resolved", "resolution": resolution},
        activity_event="resolved",
    )
