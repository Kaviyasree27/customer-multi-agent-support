import uuid
import random
import string
from datetime import datetime, timezone
from functools import wraps

from bson import ObjectId
from flask import jsonify
from flask_jwt_extended import get_jwt, verify_jwt_in_request


def now():
    return datetime.now(timezone.utc)


def new_id():
    return str(uuid.uuid4())


def order_number():
    return "ORD-" + "".join(random.choices(string.digits, k=8))


def ticket_number():
    return "TKT-" + "".join(random.choices(string.digits, k=8))


def to_json(doc):
    """Recursively convert Mongo doc (dict/list) into JSON-serializable form."""
    if doc is None:
        return None
    if isinstance(doc, list):
        return [to_json(d) for d in doc]
    if isinstance(doc, dict):
        out = {}
        for k, v in doc.items():
            if k == "_id":
                out["id"] = str(v)
            elif k == "password_hash":
                continue
            elif isinstance(v, ObjectId):
                out[k] = str(v)
            elif isinstance(v, datetime):
                out[k] = v.isoformat()
            elif isinstance(v, (dict, list)):
                out[k] = to_json(v)
            else:
                out[k] = v
        return out
    return doc


def error_response(message, status=400, code=None):
    payload = {"error": message}
    if code:
        payload["code"] = code
    return jsonify(payload), status


def role_required(*roles):
    """Decorator to restrict a route to specific JWT-embedded roles."""

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            if claims.get("role") not in roles:
                return error_response("Forbidden: insufficient role", 403)
            return fn(*args, **kwargs)

        return wrapper

    return decorator
