from agents.base_agent import call_llm, AgentResult
from models import order_model

SYSTEM_PROMPT = """You are the Order Management Agent inside a customer support system.
You are given real order data retrieved from the database. Summarize it naturally and
helpfully for the customer. Never fabricate order details beyond what is given. If asked
to cancel and the order data says it is not cancellable, explain why clearly and
sympathetically, and offer to raise a complaint/ticket instead. Keep replies concise."""


def _format_order(o: dict) -> str:
    items = ", ".join(f"{i.get('qty', 1)}x {i.get('name')}" for i in o.get("items", []))
    return (
        f"Order {o['order_number']}: status={o['status']}, items=[{items}], "
        f"total={o.get('total_amount')}, placed_at={o['created_at']}"
    )


def handle_order_status(customer_id: str, message: str, order_number: str = None) -> AgentResult:
    if order_number:
        order = order_model.find_order_by_number(order_number, customer_id=customer_id)
        orders = [order] if order else []
    else:
        orders = order_model.list_orders_for_customer(customer_id)[:5]

    if not orders:
        reply = call_llm(
            SYSTEM_PROMPT,
            f"Customer asked: \"{message}\". No matching orders were found in the database "
            f"for this customer (order_number searched: {order_number}). Tell them clearly, "
            f"and ask them to double check the order number or check their order list.",
        )
        return AgentResult(reply=reply, agent="order_agent", data={"orders": []})

    order_summaries = "\n".join(_format_order(o) for o in orders)
    reply = call_llm(
        SYSTEM_PROMPT,
        f"Customer asked: \"{message}\"\n\nReal order data:\n{order_summaries}\n\n"
        f"Respond to the customer using only this data.",
    )
    return AgentResult(reply=reply, agent="order_agent", data={"orders": [_public(o) for o in orders]})


def handle_cancellation(customer_id: str, message: str, order_number: str = None) -> AgentResult:
    if not order_number:
        orders = order_model.list_orders_for_customer(customer_id)
        cancellable = [o for o in orders if order_model.is_cancellable(o)[0]]
        if len(cancellable) == 1:
            order_number = cancellable[0]["order_number"]
        else:
            reply = call_llm(
                SYSTEM_PROMPT,
                f"Customer wants to cancel an order but did not give an order number. "
                f"Ask them which order number they mean. Message: \"{message}\"",
            )
            return AgentResult(reply=reply, agent="order_agent", data={"needs_order_number": True})

    order = order_model.find_order_by_number(order_number, customer_id=customer_id)
    if not order:
        reply = f"I couldn't find an order with number {order_number} on your account. Could you double-check it?"
        return AgentResult(reply=reply, agent="order_agent", data={"orders": []})

    ok, reason = order_model.is_cancellable(order)
    if not ok:
        reply = call_llm(
            SYSTEM_PROMPT,
            f"Customer wants to cancel order {order_number}, but it is NOT cancellable. "
            f"Reason: {reason}. Order status: {order['status']}. Explain this to the customer "
            f"kindly and offer to file a complaint/ticket if they still need help.",
        )
        return AgentResult(reply=reply, agent="order_agent", data={"cancelled": False, "order": _public(order)},
                            actions=["cancellation_denied"])

    updated, err = order_model.cancel_order(order["_id"], reason="Cancelled via AI chat")
    reply = call_llm(
        SYSTEM_PROMPT,
        f"Order {order_number} was just successfully cancelled. Confirm this warmly to the "
        f"customer and let them know refund/next steps typically take a few business days.",
    )
    return AgentResult(reply=reply, agent="order_agent", data={"cancelled": True, "order": _public(updated)},
                        actions=["order_cancelled"])


def _public(o: dict) -> dict:
    return {
        "order_number": o["order_number"],
        "status": o["status"],
        "items": o.get("items", []),
        "total_amount": o.get("total_amount"),
        "created_at": o["created_at"].isoformat() if hasattr(o["created_at"], "isoformat") else o["created_at"],
    }
