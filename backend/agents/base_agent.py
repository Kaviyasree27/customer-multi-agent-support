
import json
import re

from groq import Groq
from config import Config


# Initialize Groq client
_client = (
    Groq(api_key=Config.GROQ_API_KEY)
    if Config.GROQ_API_KEY
    else None
)


class LLMUnavailableError(Exception):
    pass


def call_llm(
    system_prompt: str,
    user_prompt: str,
    max_tokens=800,
    temperature=0.4
) -> str:
    """
    Single entry point for every AI agent's LLM calls.
    Uses Groq instead of Anthropic.
    """

    if _client is None:
        raise LLMUnavailableError(
            "GROQ_API_KEY is not configured on the server. "
            "Set it in backend/.env."
        )

    response = _client.chat.completions.create(
        model=Config.GROQ_MODEL,
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        max_tokens=max_tokens,
        temperature=temperature
    )

    answer = response.choices[0].message.content

    return (answer or "").strip()


def call_llm_json(
    system_prompt: str,
    user_prompt: str,
    max_tokens=500
) -> dict:
    """
    Requests JSON output from the model and parses it defensively.
    Handles markdown code fences and additional surrounding text.
    """

    raw = call_llm(
        system_prompt
        + "\n\nRespond with ONLY valid JSON. "
          "No prose, no markdown fences.",
        user_prompt,
        max_tokens=max_tokens,
        temperature=0.1
    )

    # Remove markdown code fences
    cleaned = re.sub(
        r"```(?:json)?",
        "",
        raw,
        flags=re.IGNORECASE
    ).replace("```", "").strip()

    # Extract JSON object if surrounded by additional text
    decoder = json.JSONDecoder()

    start = cleaned.find("{")

    if start == -1:
        return {}

    try:
        result, _ = decoder.raw_decode(cleaned[start:])

        if isinstance(result, dict):
            return result

        return {}

    except json.JSONDecodeError:
        return {}


class AgentResult:
    """
    Uniform return shape every agent produces,
    allowing the orchestrator to compose them.
    """

    def __init__(
        self,
        reply: str,
        data=None,
        agent="",
        actions=None
    ):
        self.reply = reply
        self.data = data or {}
        self.agent = agent
        self.actions = actions or []

    def to_dict(self):
        return {
            "reply": self.reply,
            "data": self.data,
            "agent": self.agent,
            "actions": self.actions
        }
