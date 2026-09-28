from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from models import user_model
from utils.helpers import to_json, error_response

bp = Blueprint("profile", __name__, url_prefix="/api/profile")


@bp.get("")
@jwt_required()
def get_profile():
    user = user_model.find_by_id(get_jwt_identity())
    if not user:
        return error_response("User not found.", 404)
    return jsonify({"user": to_json(user)})


@bp.put("")
@jwt_required()
def update_profile():
    user_id = get_jwt_identity()
    body = request.get_json(force=True) or {}
    updates = {}
    for field in ("name", "phone", "address"):
        if field in body and isinstance(body[field], str):
            updates[field] = body[field].strip()

    if "password" in body and body["password"]:
        if len(body["password"]) < 6:
            return error_response("Password must be at least 6 characters.")
        updates["password_hash"] = user_model.hash_password(body["password"])

    if not updates:
        return error_response("No valid fields to update.")

    user = user_model.update_profile(user_id, updates)
    return jsonify({"user": to_json(user)})
