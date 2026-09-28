import bcrypt
from extensions import db
from utils.helpers import new_id, now


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except Exception:
        return False


def create_user(name, email, password, role="customer", phone=""):
    user = {
        "_id": new_id(),
        "name": name,
        "email": email.lower().strip(),
        "phone": phone,
        "password_hash": hash_password(password),
        "role": role,
        "created_at": now(),
        "updated_at": now(),
    }
    db.users.insert_one(user)
    return user


def find_by_email(email):
    return db.users.find_one({"email": email.lower().strip()})


def find_by_id(user_id):
    return db.users.find_one({"_id": user_id})


def update_profile(user_id, updates: dict):
    updates["updated_at"] = now()
    db.users.update_one({"_id": user_id}, {"$set": updates})
    return find_by_id(user_id)


def list_customers(search=None, limit=200):
    query = {"role": "customer"}
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
        ]
    return list(db.users.find(query).sort("created_at", -1).limit(limit))


def ensure_admin(email, password, name="System Admin"):
    existing = find_by_email(email)
    if existing:
        return existing
    return create_user(name, email, password, role="admin")
