"""
Adds sample FAQs to the knowledge base (skips any question that already exists).

Run from backend/:
    python seed_faqs.py

The answers are SAMPLE content so retrieval has something to search.
Edit the numbers/policies to match your demo store before showing it to anyone.
"""

from datetime import datetime, timezone

from extensions import db
from models.feedback_model import list_faqs

FAQS = [
    ("returns", "What is your return policy?",
     "You can return most items within 7 days of delivery if they are unused and in original packaging."),
    ("returns", "How do I return a product?",
     "Open My Orders, choose the order, and select Return. Pack the item in its original packaging and hand it to the pickup agent."),
    ("returns", "What should I do if my item arrives damaged?",
     "Please report it within 48 hours of delivery with a photo of the damage by raising a complaint from the chat or the Tickets page."),
    ("returns", "What if I received the wrong item?",
     "Raise a complaint with your order number and a photo of the item received. Our team will review it and follow up."),
    ("returns", "Can I exchange a product for a different size or color?",
     "Exchanges are available for eligible items within 7 days of delivery, subject to stock availability."),
    ("refunds", "How long do refunds take?",
     "Approved refunds are sent to the original payment method within 5 to 7 business days after the returned item is received."),
    ("shipping", "How long does shipping take?",
     "Standard delivery usually takes 3 to 7 business days depending on your location."),
    ("shipping", "How much does shipping cost?",
     "Shipping is free on orders above the free-shipping threshold shown at checkout. Smaller orders carry a flat delivery fee."),
    ("shipping", "What should I do if my order is delayed?",
     "Check the latest status under My Orders. If it is past the expected date, raise a complaint and we will look into it."),
    ("shipping", "Do you ship internationally?",
     "Currently we deliver only within the country. International shipping is not available yet."),
    ("orders", "How can I track my order?",
     "Go to My Orders and open the order to see its current status, or ask me here with your order number."),
    ("orders", "Can I cancel my order?",
     "Orders can be cancelled before they are shipped. Ask me here with your order number, or use My Orders."),
    ("orders", "Can I change my delivery address after placing an order?",
     "The address can be changed only before the order is shipped. Contact support with your order number as soon as possible."),
    ("payments", "What payment methods do you accept?",
     "We accept credit and debit cards, UPI, net banking, and cash on delivery for eligible orders."),
    ("payments", "Why was my payment declined?",
     "Payments can fail due to insufficient balance, incorrect card details, or bank restrictions. Please retry or use another payment method."),
    ("payments", "How do I apply a discount code?",
     "Enter the code in the Apply Coupon box on the checkout page before paying."),
    ("warranty", "Is there a warranty on products?",
     "Electronics carry a manufacturer warranty. The period is listed on the product page."),
    ("account", "How do I reset my password?",
     "On the login page choose Forgot Password and follow the steps to set a new password."),
    ("account", "How do I update my profile or address?",
     "Open Profile from the menu, edit your details, and save."),
    ("support", "How do I contact customer support?",
     "Use this chat, raise a ticket from the Tickets page, or ask to be connected with a human agent."),
    ("refunds", "What is your refund policy?",
     "Refunds are issued to the original payment method after the returned item is received and passes a quality check. Items must be returned within 7 days of delivery."),
    ("refunds", "When will I get my refund?",
     "Once the returned item reaches us and is approved, the refund is processed within 5 to 7 business days. Your bank may take a little longer to show it."),
    ("refunds", "How do I check the status of my refund?",
     "Open My Orders and select the returned order to see its refund status. You can also ask me here with your order number."),
    ("refunds", "Will I get a refund if I cancel my order?",
     "If you cancel before the order ships and you already paid online, the amount is returned to your original payment method."),
    ("returns", "When will my returned item be picked up?",
     "After you request a return, pickup is usually scheduled within 2 to 3 business days. You will see the pickup date on the order page."),
    ("returns", "Are there items that cannot be returned?",
     "Items such as innerwear, personalised products, and opened consumables cannot be returned unless they arrive damaged."),
]


def main():
    existing = {str(f.get("question", "")).strip().lower() for f in list_faqs()}
    now = datetime.now(timezone.utc)
    added = 0

    for category, question, answer in FAQS:
        if question.strip().lower() in existing:
            continue
        db.faqs.insert_one(
            {
                "question": question,
                "answer": answer,
                "category": category,
                "created_at": now,
                "updated_at": now,
            }
        )
        added += 1

    print(f"Added {added} FAQs ({len(FAQS) - added} already existed).")


def _run():
    try:
        from app import create_app
    except ImportError:
        return main()
    with create_app().app_context():
        main()


if __name__ == "__main__":
    _run()