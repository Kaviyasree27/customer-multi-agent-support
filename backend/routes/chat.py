
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from agents.orchestrator import handle_message
from models import conversation_model
from utils.helpers import to_json, error_response

bp = Blueprint("chat", __name__, url_prefix="/api/chat")


# ==========================================
# Send Customer Message
# ==========================================

@bp.post("/message")
@jwt_required()
def send_message():
    customer_id = get_jwt_identity()

    body = request.get_json(silent=True) or {}

    message = (body.get("message") or "").strip()
    conversation_id = body.get("conversation_id")

    if not message:
        return error_response("Message cannot be empty.", 400)

    if not isinstance(message, str):
        return error_response("Invalid message format.", 400)

    try:
        result = handle_message(
            customer_id,
            message,
            conversation_id
        )

        return jsonify(result), 200

    except Exception:
        import logging
        logging.exception("Chat processing failed")

        return error_response(
            "Unable to process your message. Please try again.",
            500
        )


# ==========================================
# List Customer Conversations
# ==========================================

@bp.get("/conversations")
@jwt_required()
def list_conversations():
    customer_id = get_jwt_identity()

    try:
        conversations = (
            conversation_model.list_conversations_for_customer(
                customer_id
            )
        )

        return jsonify({
            "conversations": to_json(conversations)
        }), 200

    except Exception:
        import logging
        logging.exception("Failed to retrieve conversations")

        return error_response(
            "Unable to retrieve conversations.",
            500
        )


# ==========================================
# Retrieve Conversation Messages
# ==========================================

@bp.get("/conversations/<conversation_id>/messages")
@jwt_required()
def conversation_messages(conversation_id):
    customer_id = get_jwt_identity()

    try:
        conversation = conversation_model.find_conversation(
            conversation_id
        )

        if not conversation:
            return error_response(
                "Conversation not found.",
                404
            )

        if str(conversation["customer_id"]) != str(customer_id):
            return error_response(
                "You are not authorized to access this conversation.",
                403
            )

        messages = conversation_model.get_history(
            conversation_id,
            limit=200
        )

        return jsonify({
            "messages": to_json(messages)
        }), 200

    except Exception:
        import logging
        logging.exception("Failed to retrieve conversation messages")

        return error_response(
            "Unable to retrieve conversation messages.",
            500
        )
