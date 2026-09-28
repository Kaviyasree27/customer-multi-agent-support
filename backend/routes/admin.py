from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required

from extensions import db
from models import user_model, order_model, ticket_model, conversation_model, feedback_model
from utils.helpers import to_json, error_response, role_required

bp = Blueprint("admin", __name__, url_prefix="/api/admin")


# ---------------- Customers ----------------

@bp.get("/customers")
@role_required("admin")
def customers():
    search = request.args.get("search")
    return jsonify({"customers": to_json(user_model.list_customers(search))})


@bp.get("/customers/<customer_id>")
@role_required("admin")
def customer_detail(customer_id):
    user = user_model.find_by_id(customer_id)
    if not user:
        return error_response("Customer not found.", 404)
    orders = order_model.list_orders_for_customer(customer_id)
    tickets = ticket_model.list_tickets_for_customer(customer_id)
    convos = conversation_model.list_conversations_for_customer(customer_id)
    return jsonify({
        "customer": to_json(user),
        "orders": to_json(orders),
        "tickets": to_json(tickets),
        "conversations": to_json(convos),
    })


# ---------------- Orders ----------------

@bp.get("/orders")
@role_required("admin")
def all_orders():
    status = request.args.get("status")
    return jsonify({"orders": to_json(order_model.list_all_orders(status))})


@bp.put("/orders/<order_id>/status")
@role_required("admin")
def set_order_status(order_id):
    body = request.get_json(force=True) or {}
    status = body.get("status")
    valid = {"placed", "processing", "confirmed", "shipped", "delivered", "cancelled"}
    if status not in valid:
        return error_response(f"Status must be one of {sorted(valid)}.")
    order = order_model.update_status(order_id, status)
    return jsonify({"order": to_json(order)})


# ---------------- Tickets ----------------

@bp.get("/tickets")
@role_required("admin")
def all_tickets():
    status = request.args.get("status")
    priority = request.args.get("priority")
    escalated_param = request.args.get("escalated")
    escalated = None
    if escalated_param is not None:
        escalated = escalated_param.lower() == "true"
    return jsonify({"tickets": to_json(ticket_model.list_all_tickets(status, priority, escalated))})


@bp.put("/tickets/<ticket_id>/status")
@role_required("admin")
def set_ticket_status(ticket_id):
    body = request.get_json(force=True) or {}
    status = body.get("status")
    valid = {"open", "in_progress", "resolved", "closed", "escalated"}
    if status not in valid:
        return error_response(f"Status must be one of {sorted(valid)}.")
    ticket = ticket_model.update_ticket(ticket_id, {"status": status}, activity_event=f"status -> {status}")
    return jsonify({"ticket": to_json(ticket)})


@bp.put("/tickets/<ticket_id>/resolve")
@role_required("admin")
def resolve_ticket(ticket_id):
    body = request.get_json(force=True) or {}
    resolution = (body.get("resolution") or "").strip()
    if not resolution:
        return error_response("Resolution text is required.")
    ticket = ticket_model.resolve_ticket(ticket_id, resolution)
    return jsonify({"ticket": to_json(ticket)})


@bp.put("/tickets/<ticket_id>/assign")
@role_required("admin")
def assign_ticket(ticket_id):
    body = request.get_json(force=True) or {}
    assignee = (body.get("assigned_to") or "").strip()
    ticket = ticket_model.update_ticket(
        ticket_id, {"assigned_to": assignee}, activity_event=f"assigned to {assignee}"
    )
    return jsonify({"ticket": to_json(ticket)})


@bp.get("/escalations")
@role_required("admin")
def escalations():
    tickets = ticket_model.list_all_tickets(escalated=True)
    return jsonify({"tickets": to_json(tickets)})


# ---------------- Conversations / agent activity ----------------

@bp.get("/conversations")
@role_required("admin")
def all_conversations():
    status = request.args.get("status")
    return jsonify({"conversations": to_json(conversation_model.list_all_conversations(status))})


@bp.get("/conversations/<conversation_id>/messages")
@role_required("admin")
def conversation_messages(conversation_id):
    msgs = conversation_model.get_history(conversation_id, limit=500)
    return jsonify({"messages": to_json(msgs)})


# ---------------- FAQ / knowledge base management (feeds the RAG Query Agent) ----------------

@bp.get("/faqs")
@role_required("admin")
def list_faqs():
    return jsonify({"faqs": to_json(feedback_model.list_faqs())})


@bp.post("/faqs")
@role_required("admin")
def add_faq():
    body = request.get_json(force=True) or {}
    q = (body.get("question") or "").strip()
    a = (body.get("answer") or "").strip()
    category = (body.get("category") or "general").strip()
    if not q or not a:
        return error_response("Question and answer are required.")
    faq = feedback_model.add_faq(q, a, category)
    return jsonify({"faq": to_json(faq)}), 201


# ---------------- Analytics (fully computed from live MongoDB data) ----------------

@bp.get("/analytics")
@role_required("admin")
def analytics():
    total_customers = db.users.count_documents({"role": "customer"})
    total_orders = db.orders.count_documents({})
    total_tickets = db.tickets.count_documents({})
    open_tickets = db.tickets.count_documents({"status": {"$in": ["open", "in_progress", "escalated"]}})
    escalated_tickets = db.tickets.count_documents({"escalated": True})
    total_conversations = db.conversations.count_documents({})

    orders_by_status = list(db.orders.aggregate([
        {"$group": {"_id": "$status", "count": {"$sum": 1}}}
    ]))
    tickets_by_status = list(db.tickets.aggregate([
        {"$group": {"_id": "$status", "count": {"$sum": 1}}}
    ]))
    tickets_by_priority = list(db.tickets.aggregate([
        {"$group": {"_id": "$priority", "count": {"$sum": 1}}}
    ]))
    tickets_by_category = list(db.tickets.aggregate([
        {"$group": {"_id": "$category", "count": {"$sum": 1}}}
    ]))
    agent_activity = list(db.messages.aggregate([
        {"$match": {"role": "agent"}},
        {"$group": {"_id": "$meta.agent", "count": {"$sum": 1}}}
    ]))
    revenue_pipeline = list(db.orders.aggregate([
        {"$match": {"status": {"$ne": "cancelled"}}},
        {"$group": {"_id": None, "total": {"$sum": "$total_amount"}}}
    ]))
    revenue = revenue_pipeline[0]["total"] if revenue_pipeline else 0

    rating = feedback_model.average_rating()

    return jsonify({
        "totals": {
            "customers": total_customers,
            "orders": total_orders,
            "tickets": total_tickets,
            "open_tickets": open_tickets,
            "escalated_tickets": escalated_tickets,
            "conversations": total_conversations,
            "revenue": round(revenue, 2),
            "avg_rating": rating["avg"],
            "feedback_count": rating["count"],
        },
        "orders_by_status": {r["_id"]: r["count"] for r in orders_by_status},
        "tickets_by_status": {r["_id"]: r["count"] for r in tickets_by_status},
        "tickets_by_priority": {r["_id"]: r["count"] for r in tickets_by_priority},
        "tickets_by_category": {r["_id"]: r["count"] for r in tickets_by_category},
        "agent_activity": {(r["_id"] or "unknown"): r["count"] for r in agent_activity},
    })
