
from datetime import datetime, timedelta, timezone

from extensions import db
from config import Config
from utils.helpers import new_id, now, order_number


def _to_utc_datetime(value):
    """
    Convert datetime values to timezone-aware UTC.

    MongoDB/PyMongo may return naive datetimes even when
    the original datetime was timezone-aware.
    """
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))

    if not isinstance(value, datetime):
        raise ValueError("Invalid order timestamp.")

    if value.tzinfo is None:
        # MongoDB naive datetimes are treated as UTC.
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def create_order(customer_id, items, total_amount, shipping_address=""):
    created_at = now()

    order = {
        "_id": new_id(),
        "order_number": order_number(),
        "customer_id": customer_id,
        "items": items,
        "total_amount": total_amount,
        "shipping_address": shipping_address,
        "status": "placed",
        "created_at": created_at,
        "updated_at": created_at,
        "history": [
            {
                "status": "placed",
                "at": created_at.isoformat(),
            }
        ],
    }

    db.orders.insert_one(order)

    return order


def list_orders_for_customer(customer_id):
    return list(
        db.orders.find(
            {"customer_id": customer_id}
        ).sort("created_at", -1)
    )


def list_all_orders(status=None, limit=300):
    query = {}

    if status:
        query["status"] = status

    return list(
        db.orders.find(query)
        .sort("created_at", -1)
        .limit(limit)
    )


def find_order(order_id):
    return db.orders.find_one({"_id": order_id})


def find_order_by_number(order_number_str, customer_id=None):
    query = {"order_number": order_number_str}

    if customer_id:
        query["customer_id"] = customer_id

    return db.orders.find_one(query)


def is_cancellable(order: dict):
    """
    Check whether an order can be cancelled.

    Cancellation requires:
    1. Order exists.
    2. Order status is eligible.
    3. Cancellation window has not expired.
    """

    if not order:
        return False, "Order not found."

    status = order.get("status", "").lower()

    if status not in Config.CANCELLABLE_STATUSES:
        return False, (
            f"Order is already '{status}' "
            "and can no longer be cancelled."
        )

    placed_at = order.get("created_at")

    if not placed_at:
        return False, "Order placement time is unavailable."

    try:
        placed_at = _to_utc_datetime(placed_at)
        current_time = _to_utc_datetime(now())

    except (ValueError, TypeError):
        return False, "Unable to validate order placement time."

    cancellation_window = timedelta(
        hours=Config.ORDER_CANCELLATION_WINDOW_HOURS
    )

    elapsed_time = current_time - placed_at

    if elapsed_time > cancellation_window:
        return False, (
            f"Cancellation window of "
            f"{Config.ORDER_CANCELLATION_WINDOW_HOURS}h has passed."
        )

    return True, None


def cancel_order(order_id, reason=""):
    """
    Cancel an eligible order and record the cancellation
    in its history.
    """

    order = find_order(order_id)

    if not order:
        return None, "Order not found."

    ok, message = is_cancellable(order)

    if not ok:
        return None, message

    cancelled_at = now()

    db.orders.update_one(
        {"_id": order_id},
        {
            "$set": {
                "status": "cancelled",
                "cancel_reason": reason,
                "updated_at": cancelled_at,
            },
            "$push": {
                "history": {
                    "status": "cancelled",
                    "at": cancelled_at.isoformat(),
                    "reason": reason,
                }
            },
        },
    )

    return find_order(order_id), None


def update_status(order_id, status):
    """
    Update order status from the admin dashboard
    and append the change to order history.
    """

    order = find_order(order_id)

    if not order:
        return None

    updated_at = now()

    db.orders.update_one(
        {"_id": order_id},
        {
            "$set": {
                "status": status,
                "updated_at": updated_at,
            },
            "$push": {
                "history": {
                    "status": status,
                    "at": updated_at.isoformat(),
                }
            },
        },
    )

    return find_order(order_id)
