"""PII redaction layer — replaces identifiers with placeholders before any
text leaves the process, and restores them afterwards.

Patterns covered:
- GSTIN: 15-char Indian GST number (2 digits + 10 chars + 4 chars + Z + 1 char)
- Udyam: UDYAM-XX-00-NNNNNNN
- Phone: 10-digit Indian mobile numbers
- Email: standard email addresses
- Signatory names: detected via common name tokens (best-effort)
"""
from __future__ import annotations

import re

# GSTIN: 15 chars — 2 state digits, 10 PAN chars, 1 entity, 1 Z, 1 checksum
_GSTIN_RE = re.compile(r"\b\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}Z[A-Z\d]\b", re.IGNORECASE)
# Udyam: UDYAM-XX-00-NNNNNNN
_UDYAM_RE = re.compile(r"\bUDYAM-[A-Z]{2}-00-\d{7}\b", re.IGNORECASE)
# Phone: 10-digit Indian mobile (starts with 6-9)
_PHONE_RE = re.compile(r"(?<![\d+])\+?91?[\s-]?[6-9]\d{9}(?!\d)")
# Email
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

# Common name tokens for signatory name detection (best effort)
_NAME_TOKENS = {
    "proprietor", "owner", "signatory", "director", "partner", "manager",
    "authorized", "authorised", "signs", "on behalf", "for and on behalf",
}

# Placeholder tokens
_GSTIN_PLACEHOLDER = "[GSTIN_REDACTED]"
_UDYAM_PLACEHOLDER = "[UDYAM_REDACTED]"
_PHONE_PLACEHOLDER = "[PHONE_REDACTED]"
_EMAIL_PLACEHOLDER = "[EMAIL_REDACTED]"
_NAME_PLACEHOLDER = "[NAME_REDACTED]"


class PIIRedactor:
    """Redacts PII from text and tracks replacements so they can be restored."""

    def __init__(self) -> None:
        self._mapping: dict[str, str] = {}  # placeholder -> original value

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def redact(self, text: str) -> str:
        """Return text with PII replaced by placeholders."""
        self._mapping = {}
        text = self._replace(_GSTIN_RE, _GSTIN_PLACEHOLDER, text)
        text = self._replace(_UDYAM_RE, _UDYAM_PLACEHOLDER, text)
        text = self._replace(_PHONE_RE, _PHONE_PLACEHOLDER, text)
        text = self._replace(_EMAIL_RE, _EMAIL_PLACEHOLDER, text)
        text = self._redact_names(text)
        return text

    def restore(self, text: str) -> str:
        """Restore original PII values from placeholders."""
        for placeholder, original in self._mapping.items():
            text = text.replace(placeholder, original)
        return text

    def contains_raw_pii(self, text: str) -> bool:
        """Return True if any raw (unredacted) PII pattern is found."""
        return bool(
            _GSTIN_RE.search(text)
            or _UDYAM_RE.search(text)
            or _PHONE_RE.search(text)
            or _EMAIL_RE.search(text)
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _replace(self, pattern: re.Pattern[str], placeholder: str, text: str) -> str:
        def repl(m: re.Match[str]) -> str:
            original = m.group(0)
            key = f"{placeholder[:-1]}_{len(self._mapping)}]"  # unique suffix
            self._mapping[key] = original
            return key

        return pattern.sub(repl, text)

    def _redact_names(self, text: str) -> str:
        """Best-effort redaction of names appearing near name tokens."""
        # Match patterns like "Proprietor: John Doe" or "Signed by: Jane Smith"
        name_pat = re.compile(
            r"(?i)(?:\b(?:proprietor|owner|signatory|director|partner|manager|authorized|authorised)\b[:\s]+)([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})"
        )

        def repl(m: re.Match[str]) -> str:
            original = m.group(2) if m.lastindex and m.lastindex >= 2 else m.group(0)
            key = f"[NAME_REDACTED_{len(self._mapping)}]"
            self._mapping[key] = original
            return m.group(1) + " " + key if m.lastindex and m.lastindex >= 2 else key

        return name_pat.sub(repl, text)


def redact_pii(text: str) -> tuple[str, PIIRedactor]:
    """Convenience: redact PII and return (redacted_text, redactor)."""
    redactor = PIIRedactor()
    return redactor.redact(text), redactor


def assert_no_raw_pii(text: str, label: str = "text") -> None:
    """Raise AssertionError if raw PII is found — for use in tests."""
    redactor = PIIRedactor()
    assert not redactor.contains_raw_pii(text), (
        f"Raw PII detected in {label}; identifiers must be redacted before LLM calls"
    )
