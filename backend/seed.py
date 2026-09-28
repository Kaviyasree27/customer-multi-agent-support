"""
Optional convenience script. Populates MongoDB with:
- one demo customer account
- a couple of real orders for that customer
- a starter FAQ knowledge base (admin-editable afterwards from the Admin Dashboard)

Nothing here is used as canned chat responses -- the AI agents still read this data
live from MongoDB and reason over it with the LLM at request time.

Run with:  python seed.py
"""
from models import user_model, order_model, feedback_model

DEMO_EMAIL = "demo@customer.local"
DEMO_PASSWORD = "Demo1234!"


def run():
    user = user_model.find_by_email(DEMO_EMAIL)
    if not user:
        user = user_model.create_user("Demo Customer", DEMO_EMAIL, DEMO_PASSWORD, role="customer", phone="9999999999")
        print(f"Created demo customer: {DEMO_EMAIL} / {DEMO_PASSWORD}")
    else:
        print("Demo customer already exists.")

    existing_orders = order_model.list_orders_for_customer(user["_id"])
    if not existing_orders:
        o1 = order_model.create_order(
            user["_id"],
            items=[{"name": "Wireless Earbuds", "qty": 1, "price": 49.99}],
            total_amount=49.99,
            shipping_address="221B Demo Street, Chennai, IN",
        )
        o2 = order_model.create_order(
            user["_id"],
            items=[{"name": "USB-C Charger", "qty": 2, "price": 15.0}],
            total_amount=30.0,
            shipping_address="221B Demo Street, Chennai, IN",
        )
        order_model.update_status(o2["_id"], "delivered")
        print(f"Created demo orders: {o1['order_number']}, {o2['order_number']}")
    else:
        print("Demo orders already exist.")

    if feedback_model.faq_count() == 0:
        faqs = [
            ("What is your return policy?",
             "Items can be returned within 30 days of delivery if unused and in original packaging. "
             "Refunds are issued to the original payment method within 5-7 business days."),
            ("How long does shipping take?",
             "Standard shipping takes 3-5 business days. Express shipping (where available) takes 1-2 business days."),
            ("Can I change my shipping address after placing an order?",
             "Address changes are possible only before the order enters 'processing' status. "
             "Contact support immediately via chat and we'll try to update it."),
            ("How do I track my order?",
             "Go to Orders in your dashboard, or ask the AI chat 'where is my order <order number>' "
             "for a live status update."),
            ("What payment methods are accepted?",
             "We accept major credit/debit cards, UPI, and net banking at checkout."),
            ("How do I cancel an order?",
             "Orders can be cancelled within 24 hours of placement as long as they haven't shipped yet. "
             "Use the Cancel button on the order or ask the AI chat to cancel it for you."),
        ]
        for q, a in faqs:
            feedback_model.add_faq(q, a, category="general")
        print(f"Seeded {len(faqs)} FAQ articles.")
    else:
        print("FAQ knowledge base already populated.")


if __name__ == "__main__":
    run()
