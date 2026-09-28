from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from agents.complaint_agent import create_ticket_from_message
from models import ticket_model, feedback_model
from utils.helpers import to_json, error_response

bp = Blueprint("tickets", __name__, url_prefix="/api/tickets")


@bp.get("")
@jwt_required()
def list_tickets():
    customer_id = get_jwt_identity()
    tickets = ticket_model.list_tickets_for_customer(customer_id)
    return jsonify({"tickets": to_json(tickets)})


@bp.post("")
@jwt_required()
def create_ticket():
    """Manual complaint form (outside the chat). Still routed through the Complaint
    Agent so category/priority are dynamically assigned by the AI, not hardcoded."""
    customer_id = get_jwt_identity()
    body = request.get_json(force=True) or {}
    subject = (body.get("subject") or "").strip()
    description = (body.get("description") or "").strip()
    order_id = body.get("order_id")

    if not subject or not description:
        return error_response("Subject and description are required.")

    message = f"{subject}. {description}"
    result = create_ticket_from_message(customer_id, message, "(submitted via ticket form)", order_id=order_id)
    return jsonify(result.to_dict()), 201


@bp.get("/<ticket_id>")
@jwt_required()
def get_ticket(ticket_id):
    customer_id = get_jwt_identity()
    ticket = ticket_model.find_ticket(ticket_id)
    if not ticket or ticket["customer_id"] != customer_id:
        return error_response("Ticket not found.", 404)
    return jsonify({"ticket": to_json(ticket)})


# --- Feedback (kept in the same blueprint file for simplicity) ---

feedback_bp = Blueprint("feedback", __name__, url_prefix="/api/feedback")


@feedback_bp.post("")
@jwt_required()
def submit_feedback():
    customer_id = get_jwt_identity()
    body = request.get_json(force=True) or {}
    rating = body.get("rating")
    comment = (body.get("comment") or "").strip()
    ticket_id = body.get("ticket_id")
    conversation_id = body.get("conversation_id")

    if rating is None or not (1 <= int(rating) <= 5):
        return error_response("Rating must be an integer between 1 and 5.")

    fb = feedback_model.submit_feedback(customer_id, rating, comment, ticket_id, conversation_id)
    return jsonify({"feedback": to_json(fb)}), 201


@feedback_bp.get("")
@jwt_required()
def list_my_feedback():
    customer_id = get_jwt_identity()
    fb = feedback_model.list_feedback_for_customer(customer_id)
    return jsonify({"feedback": to_json(fb)})
