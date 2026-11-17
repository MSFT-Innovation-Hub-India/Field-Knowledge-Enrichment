"""Deterministic guardrails applied before anything is written (technical spec section 8, S3)."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

ERROR_CODE = re.compile(r"\b[EW]-\d{3}\b")
PART_NUMBER = re.compile(r"\b[A-Z]{2,}[A-Z0-9]*(?:-[A-Z0-9]+)*-[A-Z0-9]*\d[A-Z0-9]*(?:-[A-Z0-9]+)*\b")
MEASURE = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)\s?(°\s?C|°C|V|A|Ω|MΩ|ohms?|mm|kW|kWh|Ah|%|minutes?|mins?|hours?|hrs?|seconds?|secs?)(?![A-Za-z])", re.IGNORECASE)
TICKET_ID = re.compile(r"\bINC-\d{4}-\d{3,6}\b")

INJECTION_PATTERNS = [
    r"ignore (all |any |the )?(previous|prior|above|earlier)",
    r"disregard (all |any |the )?(previous|prior|above|instructions)",
    r"system prompt", r"you are now", r"\bact as\b", r"reveal (your|the) (prompt|instructions)",
    r"<\s*/?\s*(system|assistant|ticket|fix|sop)\b", r"https?://", r"\bjailbreak\b",
]
SECRET_PATTERNS = {
    "email": r"[\w.+-]+@[\w-]+\.[\w.-]+",
    "phone": r"(?<![A-Za-z0-9-])\+?\d[\d ]{9,13}\d(?![A-Za-z0-9-])",
    "key": r"(?i)(accountkey|sharedaccesskey|api[_-]?key|secret|password|bearer\s+[a-z0-9._-]{10,})\s*[:=]",
    "token": r"\b[A-Za-z0-9+/]{40,}={0,2}\b",
}

MAX_FIELD_CHARS = 3000
MAX_FIELD_GROWTH = 1500
MAX_NEW_SOP_CHARS = 6000


@dataclass
class GuardrailResult:
    passed: bool = True
    failed: list[str] = field(default_factory=list)

    def fail(self, reason: str) -> None:
        self.passed = False
        self.failed.append(reason)

    def as_dict(self) -> dict:
        return {"passed": self.passed, "failed": self.failed}


def _norm(text: str) -> str:
    return re.sub(r"\s+", "", text.lower().replace("°", ""))


def _measures(text: str) -> set[str]:
    return {_norm(f"{m.group(1)}{m.group(2)}") for m in MEASURE.finditer(text)}


def check_input_safety(*texts: str) -> GuardrailResult:
    """Injection / secrets / PII scan of user-supplied text."""
    res = GuardrailResult()
    blob = "\n".join(t for t in texts if t)
    for pat in INJECTION_PATTERNS:
        if re.search(pat, blob, re.IGNORECASE):
            res.fail(f"injection pattern: {pat}")
    for name, pat in SECRET_PATTERNS.items():
        if re.search(pat, blob):
            res.fail(f"possible {name} in text")
    return res


def check_generated(generated: str, allowed_sources: list[str], max_chars: int, base_text: str = "", max_growth: int | None = None) -> GuardrailResult:
    """Size, no-invented-specifics, injection/secrets for model-generated text."""
    res = GuardrailResult()
    if not generated.strip():
        res.fail("empty output")
        return res
    if len(generated) > max_chars:
        res.fail(f"too long ({len(generated)} > {max_chars})")
    if max_growth is not None and len(generated) - len(base_text) > max_growth:
        res.fail(f"grew by more than {max_growth} chars")

    allowed = "\n".join(allowed_sources)
    allowed_norm = _norm(allowed)
    allowed_measures = _measures(allowed)

    for code in set(ERROR_CODE.findall(generated)):
        if code not in allowed:
            res.fail(f"invented error code {code}")
    for part in set(PART_NUMBER.findall(generated)):
        if part not in allowed and not TICKET_ID.fullmatch(part) and _norm(part) not in allowed_norm:
            res.fail(f"invented part/identifier {part}")
    for meas in _measures(generated):
        if meas not in allowed_measures:
            res.fail(f"invented measurement {meas}")

    safety = check_input_safety(generated)
    # URLs/emails etc. in generated text are not allowed even if the input had them.
    for reason in safety.failed:
        res.fail(reason)
    return res


def check_new_sop_structure(markdown: str) -> GuardrailResult:
    res = GuardrailResult()
    for required in ("| SOP ID |", "## 1. Symptoms", "## 2. Safety", "## 3. Troubleshooting steps"):
        if required not in markdown:
            res.fail(f"missing {required}")
    return res


def check_field_structure(markdown: str) -> GuardrailResult:
    res = GuardrailResult()
    if not markdown.lstrip().startswith("## Field experience"):
        res.fail("field experience must start with the '## Field experience' heading")
    return res


def trivial_fix(fix: str) -> bool:
    text = re.sub(r"\s+", " ", fix).strip().lower()
    if len(text) < 20 or len(text.split()) < 4:
        return True
    return text in {"done", "fixed", "resolved", "ok", "n/a", "na", "as per sop"}
