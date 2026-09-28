from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, get_jwt

from models import user_model
from utils.helpers import to_json, error_response

bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@bp.post("/register")
def register():
    body = request.get_json(force=True) or {}
    name = (body.get("name") or "").strip()
    email = (body.get("email") or "").strip()
    password = body.get("password") or ""
    phone = (body.get("phone") or "").strip()

    if not name or not email or len(password) < 6:
        return error_response("Name, valid email, and a password of at least 6 characters are required.")

    if user_model.find_by_email(email):
        return error_response("An account with this email already exists.", 409)

    user = user_model.create_user(name, email, password, role="customer", phone=phone)
    token = create_access_token(identity=user["_id"], additional_claims={"role": "customer"})
    return jsonify({"token": token, "user": to_json(user)}), 201


@bp.post("/login")
def login():
    body = request.get_json(force=True) or {}
    email = (body.get("email") or "").strip()
    password = body.get("password") or ""

    user = user_model.find_by_email(email)
    if not user or not user_model.verify_password(password, user["password_hash"]):
        return error_response("Invalid email or password.", 401)

    token = create_access_token(identity=user["_id"], additional_claims={"role": user["role"]})
    return jsonify({"token": token, "user": to_json(user)})


@bp.get("/me")
@jwt_required()
def me():
    user_id = get_jwt_identity()
    user = user_model.find_by_id(user_id)
    if not user:
        return error_response("User not found.", 404)
    return jsonify({"user": to_json(user), "role": get_jwt().get("role")})
