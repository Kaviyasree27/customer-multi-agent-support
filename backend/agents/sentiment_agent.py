from agents.base_agent import call_llm_json
from config import Config
from models import ticket_model

SENTIMENT_PROMPT = """You analyze customer sentiment for a support system. Given the
message (and recent conversation history for context), return JSON:
{
  "sentiment_score": <float from -1.0 (very negative/angry) to 1.0 (very positive)>,
  "urgency": "low" | "medium" | "high" | "critical",
  "is_frustrated": true|false,
  "reason": "<short phrase>"
}
Consider repeated complaints, ALL CAPS, profanity, threats to leave/chargeback, and
explicit urgency words as signals of higher urgency / lower sentiment."""


def analyze(message: str, history_text: str) -> dict:
    prompt = f"Conversation history:\n{history_text}\n\nLatest message: \"{message}\""
    result = call_llm_json(SENTIMENT_PROMPT, prompt)
    if not result or "sentiment_score" not in result:
        result = {"sentiment_score": 0.0, "urgency": "low", "is_frustrated": False, "reason": ""}
    return result


def maybe_escalate(ticket_id: str, sentiment: dict):
    """Escalate a ticket automatically if sentiment/urgency crosses thresholds.
    Returns the escalation reason string, or None if no escalation happened."""
    if not ticket_id:
        return None

    score = sentiment.get("sentiment_score", 0.0)
    urgency = sentiment.get("urgency", "low")

    should_escalate = (
        score <= Config.SENTIMENT_ESCALATION_THRESHOLD
        or urgency in Config.URGENCY_ESCALATION_LEVELS
    )
    if not should_escalate:
        return None

    reason = sentiment.get("reason") or "Negative sentiment / high urgency detected"
    ticket_model.escalate_ticket(ticket_id, reason)
    return reason
