from extensions import db
from utils.helpers import new_id, now


def get_or_create_conversation(customer_id, conversation_id=None):
    if conversation_id:
        convo = db.conversations.find_one({"_id": conversation_id, "customer_id": customer_id})
        if convo:
            return convo
    convo = {
        "_id": new_id(),
        "customer_id": customer_id,
        "created_at": now(),
        "updated_at": now(),
        "status": "active",  # active | escalated | closed
        "last_intent": None,
        "last_sentiment": None,
    }
    db.conversations.insert_one(convo)
    return convo


def touch_conversation(conversation_id, **fields):
    fields["updated_at"] = now()
    db.conversations.update_one({"_id": conversation_id}, {"$set": fields})


def add_message(conversation_id, customer_id, role, content, meta=None):
    msg = {
        "_id": new_id(),
        "conversation_id": conversation_id,
        "customer_id": customer_id,
        "role": role,  # user | agent | system
        "content": content,
        "meta": meta or {},
        "created_at": now(),
    }
    db.messages.insert_one(msg)
    return msg


def get_history(conversation_id, limit=20):
    msgs = list(
        db.messages.find({"conversation_id": conversation_id}).sort("created_at", 1).limit(limit)
    )
    return msgs


def list_conversations_for_customer(customer_id):
    return list(db.conversations.find({"customer_id": customer_id}).sort("updated_at", -1))


def list_all_conversations(status=None, limit=200):
    query = {}
    if status:
        query["status"] = status
    return list(db.conversations.find(query).sort("updated_at", -1).limit(limit))


def find_conversation(conversation_id):
    return db.conversations.find_one({"_id": conversation_id})
