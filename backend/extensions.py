from pymongo import MongoClient
from flask_jwt_extended import JWTManager
from config import Config

_client = MongoClient(Config.MONGO_URI)
db = _client.get_default_database()

jwt = JWTManager()


def init_indexes():
    """Create indexes needed for correctness & performance. Idempotent."""
    db.users.create_index("email", unique=True)
    db.orders.create_index("customer_id")
    db.orders.create_index("order_number", unique=True)
    db.tickets.create_index("customer_id")
    db.tickets.create_index("status")
    db.conversations.create_index("customer_id")
    db.messages.create_index([("conversation_id", 1), ("created_at", 1)])
    db.feedback.create_index("customer_id")
    db.faqs.create_index("category")
