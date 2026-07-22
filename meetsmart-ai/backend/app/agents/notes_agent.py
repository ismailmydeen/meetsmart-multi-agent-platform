"""
Notes Agent
-----------
Ingests raw meeting transcript/notes text and uses Groq's free LLaMA API
to produce a structured summary plus a list of action items with owners
(matched against actual meeting participants where possible) and due
dates where mentioned.
"""
import os
import json
import re
from typing import List, Dict
from groq import Groq

GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

SYSTEM_PROMPT = """You convert raw meeting notes/transcripts into structured output.
Respond with ONLY a JSON object, no preamble, no markdown fences, in this exact shape:
{
  "summary": "2-4 sentence summary of what was discussed and decided",
  "action_items": [
    {"description": "...", "owner_email": "email or null if unclear", "due_date": "YYYY-MM-DD or null"}
  ]
}
Match owners to the participant email list given when the notes name a person or role that
corresponds to one of them. If no action items are present, return an empty list."""


def _extract_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    return json.loads(text)


def structure_notes(raw_notes: str, participant_emails: List[str]) -> Dict:
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    user_prompt = (
        f"Meeting participants: {', '.join(participant_emails)}\n\n"
        f"Raw notes:\n{raw_notes}"
    )

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        max_tokens=1000,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )

    text = response.choices[0].message.content

    try:
        parsed = _extract_json(text)
    except (json.JSONDecodeError, AttributeError):
        # Fall back gracefully rather than crashing the request
        parsed = {"summary": (text or "").strip()[:500], "action_items": []}

    parsed.setdefault("summary", "")
    parsed.setdefault("action_items", [])
    return parsed
