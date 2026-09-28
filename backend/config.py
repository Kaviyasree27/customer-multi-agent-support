import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/support_system")

    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-change-me")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=12)
    JWT_TOKEN_LOCATION = ["headers"]

    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    CORS_ORIGIN = os.getenv("CORS_ORIGIN", "http://localhost:5173")

    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@support.local")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "ChangeMe123!")

    # Business rules
    ORDER_CANCELLATION_WINDOW_HOURS = 24  # orders can be cancelled within this window of placement
    CANCELLABLE_STATUSES = {"placed", "processing", "confirmed"}

    # Escalation
    SENTIMENT_ESCALATION_THRESHOLD = -0.4  # sentiment score below this triggers auto-escalation
    URGENCY_ESCALATION_LEVELS = {"high", "critical"}
