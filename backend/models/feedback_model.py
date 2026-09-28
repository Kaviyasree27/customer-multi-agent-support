from extensions import db
from utils.helpers import new_id, now


def submit_feedback(customer_id, rating, comment="", ticket_id=None, conversation_id=None):
    fb = {
        "_id": new_id(),
        "customer_id": customer_id,
        "rating": int(rating),
        "comment": comment,
        "ticket_id": ticket_id,
        "conversation_id": conversation_id,
        "created_at": now(),
    }
    db.feedback.insert_one(fb)
    return fb


def list_feedback_for_customer(customer_id):
    return list(db.feedback.find({"customer_id": customer_id}).sort("created_at", -1))


def list_all_feedback(limit=300):
    return list(db.feedback.find({}).sort("created_at", -1).limit(limit))


def average_rating():
    pipeline = [{"$group": {"_id": None, "avg": {"$avg": "$rating"}, "count": {"$sum": 1}}}]
    result = list(db.feedback.aggregate(pipeline))
    if not result:
        return {"avg": 0, "count": 0}
    return {"avg": round(result[0]["avg"], 2), "count": result[0]["count"]}


# ---- FAQ / Knowledge base (used by the RAG-based Query Agent) ----

def add_faq(question, answer, category="general"):
    faq = {
        "_id": new_id(),
        "question": question,
        "answer": answer,
        "category": category,
        "created_at": now(),
    }
    db.faqs.insert_one(faq)
    return faq


def list_faqs():
    return list(db.faqs.find({}))


def faq_count():
    return db.faqs.count_documents({})
