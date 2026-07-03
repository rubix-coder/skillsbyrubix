"""Safety gate: runs before any remedy path. Keyword matching against safety.json."""

import re

from ayurveda_wellness_mcp import constants
from ayurveda_wellness_mcp.loader import load


def _normalize(text: str) -> str:
    text = (text or "").lower()
    text = text.replace("-", " ")
    return re.sub(r"\s+", " ", text).strip()


def triage(text: str) -> dict:
    safety = load("safety")
    norm = _normalize(text)

    matched_red = [f for f in safety["red_flags"] if f in norm]
    if matched_red:
        return {"status": "refer", "matched": matched_red, "message": constants.MEDICAL_MESSAGE}

    matched_black = [b for b in safety["blacklist"] if b in norm]
    if matched_black:
        return {
            "status": "blacklisted",
            "matched": matched_black,
            "message": constants.BLACKLIST_MESSAGE.format(matched=matched_black[0]),
        }

    active_flags = []
    for flag, keywords in safety["conditional_flags"].items():
        if any(kw in norm for kw in keywords):
            active_flags.append(flag)

    if active_flags:
        return {"status": "caution", "flags": active_flags, "message": constants.CAUTION_MESSAGE}

    return {"status": "clear"}
