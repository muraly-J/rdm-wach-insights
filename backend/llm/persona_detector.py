"""
llm/persona_detector.py
───────────────────────
Stateless persona detection from message + history.
Returns: "general" | "technical" | "technician" | "financial"
"""
from __future__ import annotations

import re
from typing import Literal

Persona = Literal["general", "technical", "technician", "financial"]

_FINANCIAL = {
    "cost", "rm", "budget", "penalty", "roi", "savings", "expenditure",
    "tariff", "tnb", "payback", "bill", "money", "financial", "revenue",
    "ringgit", "sen", "charge", "rate", "expensive",
}
_TECHNICIAN = {
    "check", "replace", "inspect", "clean", "tighten", "fault", "repair",
    "capacitor", "belt", "coil", "filter", "reading", "measurement",
    "megger", "loto", "bearing", "winding", "contactor", "relay",
    "multimeter", "clamp", "torque", "resistor",
}
_TECHNICAL = {
    "thd", "harmonic", "power factor", "phase imbalance", "impedance",
    "pf_degradation", "energy_anomaly", "fair", "algorithm", "calculation",
    "analysis", "frequency", "reactive", "apparent", "rms", "kva",
    "kvar", "kwh", "ieee", "ashrae", "nema", "waveform",
}

_EXPLICIT: dict[str, re.Pattern] = {
    "financial": re.compile(
        r"\b(financial|facilities.manager|finance|cfo|accountant)\b"
        r"|i.?m.*(finance|financial|manager)",
        re.IGNORECASE,
    ),
    "technical": re.compile(
        r"\b(engineer|engineering|technical|biomedical|bme)\b"
        r"|technical (detail|breakdown|analysis)"
        r"|i.?m.*(engineer|technical)",
        re.IGNORECASE,
    ),
    "technician": re.compile(
        r"\b(technician|mechanic|maintenance (team|staff|person)|hands.on)\b"
        r"|i.?m.*(technician|mechanic)"
        r"|explain.*(step by step|procedure|how to fix)",
        re.IGNORECASE,
    ),
    "general": re.compile(
        r"\b(explain simply|simple terms|layman|non.technical|what does (it|this|that) mean)\b"
        r"|i.?m.*(not technical|just a|new to)",
        re.IGNORECASE,
    ),
}

_ROLE_CMD = re.compile(r"/role\s+(general|technical|technician|financial)", re.IGNORECASE)


def _score(text: str) -> dict[str, int]:
    lower = text.lower()
    words = set(re.findall(r"\b\w+\b", lower))
    bigrams = set(re.findall(r"\b\w+ \w+\b", lower))
    tokens = words | bigrams
    return {
        "financial":  len(tokens & _FINANCIAL),
        "technician": len(tokens & _TECHNICIAN),
        "technical":  len(tokens & _TECHNICAL),
    }


def detect_persona(
    message: str,
    history: list[dict] | None = None,
    stated_persona: str | None = None,
) -> Persona:
    """
    Detect persona. Priority:
    1. stated_persona (from frontend role selector)
    2. /role command in message
    3. Explicit declaration regex in message
    4. Keyword scoring on message
    5. Rolling keyword scoring on last 3 history turns (half weight)
    6. Default: "general"
    """
    valid = {"general", "technical", "technician", "financial"}

    if stated_persona and stated_persona in valid:
        return stated_persona  # type: ignore[return-value]

    m = _ROLE_CMD.search(message)
    if m:
        return m.group(1).lower()  # type: ignore[return-value]

    for persona, pattern in _EXPLICIT.items():
        if pattern.search(message):
            return persona  # type: ignore[return-value]

    scores = _score(message)

    if history:
        for turn in history[-3:]:
            content = turn.get("content", "")
            if isinstance(content, str):
                h = _score(content)
                for k in scores:
                    scores[k] += h[k] // 2

    best = max(scores, key=lambda k: scores[k])
    others = max((v for k, v in scores.items() if k != best), default=0)
    if scores[best] >= 2 and scores[best] > others:
        return best  # type: ignore[return-value]

    return "general"
