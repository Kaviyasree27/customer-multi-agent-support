from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from models import order_model
from utils.helpers import to_json, error_response

bp = Blueprint("orders", __name__, url_prefix="/api/orders")


@bp.get("")
@jwt_required()
def list_orders():
    customer_id = get_jwt_identity()
    orders = order_model.list_orders_for_customer(customer_id)
    return jsonify({"orders": to_json(orders)})


@bp.post("")
@jwt_required()
def create_order():
    """Lets a customer place an order (needed so the system has real, non-mock order
    data to work with end-to-end)."""
    customer_id = get_jwt_identity()
    body = request.get_json(force=True) or {}
    items = body.get("items") or []
    address = (body.get("shipping_address") or "").strip()

    if not items or not isinstance(items, list):
        return error_response("At least one item is required.")
    try:
        total = sum(float(i.get("price", 0)) * int(i.get("qty", 1)) for i in items)
    except (TypeError, ValueError):
        return error_response("Items must include numeric price and qty.")

    order = order_model.create_order(customer_id, items, round(total, 2), address)
    return jsonify({"order": to_json(order)}), 201


@bp.get("/<order_id>")
@jwt_required()
def get_order(order_id):
    customer_id = get_jwt_identity()
    order = order_model.find_order(order_id)
    if not order or order["customer_id"] != customer_id:
        return error_response("Order not found.", 404)
    return jsonify({"order": to_json(order)})


@bp.post("/<order_id>/cancel")
@jwt_required()
def cancel_order(order_id):
    customer_id = get_jwt_identity()
    order = order_model.find_order(order_id)
    if not order or order["customer_id"] != customer_id:
        return error_response("Order not found.", 404)

    reason = (request.get_json(silent=True) or {}).get("reason", "")
    updated, err = order_model.cancel_order(order_id, reason)
    if err:
        return error_response(err, 400)
    return jsonify({"order": to_json(updated)})
