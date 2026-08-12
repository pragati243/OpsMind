"""Simple input guard implementing prompt-injection and PII scanning.

This module provides a lightweight implementation rather than depending on
external guard libraries so unit tests can run deterministically.

Behavior:
- detect common prompt-injection phrases and refuse the request immediately
- detect PII-like tokens (emails, long digit sequences, SSNs) and redact
  them before returning the sanitized question
"""

import re
from typing import NamedTuple


class InspectionResult(NamedTuple):
	refused: bool
	refusal_reason: str | None
	redacted: str
	redactions: list[dict]


_INJECTION_PATTERNS = [
	r"ignore (previous|all) instructions",
	r"you are now in developer mode",
	r"you are now",
	r"bypass( the)? (filters|restrictions)",
	r"ignore this prompt",
	r"follow these instructions instead",
	r"act as an?",
]

_PII_EMAIL = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_PII_SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_PII_LONG_DIGITS = re.compile(r"\b\d{6,}\b")


def inspect(question: str) -> InspectionResult:
	"""Inspect and sanitize an incoming question.

	Returns an InspectionResult. If `refused` is True the caller should
	refuse the request and not continue routing. Otherwise `redacted` is
	safe to pass downstream.
	"""
	if not question or not question.strip():
		return InspectionResult(False, None, question, [])

	lowered = question.lower()
	for pat in _INJECTION_PATTERNS:
		if re.search(pat, lowered):
			return InspectionResult(True, "Prompt injection detected: malicious instructions.", "", [{"type": "injection", "pattern": pat}])

	redactions: list[dict] = []
	redacted = question

	# emails
	for m in list(_PII_EMAIL.finditer(redacted)):
		span = m.span()
		token = m.group(0)
		redacted = redacted.replace(token, "[REDACTED_EMAIL]")
		redactions.append({"type": "email", "original": token, "span": span})

	# SSN-like
	for m in list(_PII_SSN.finditer(redacted)):
		token = m.group(0)
		redacted = redacted.replace(token, "[REDACTED_SSN]")
		redactions.append({"type": "ssn", "original": token, "span": m.span()})

	# long digit sequences that could be sensitive (ticket ids, account numbers)
	for m in list(_PII_LONG_DIGITS.finditer(redacted)):
		token = m.group(0)
		# avoid redacting numbers which are obviously innocuous e.g., years like 2023
		if len(token) >= 7:
			redacted = redacted.replace(token, "[REDACTED_NUMBER]")
			redactions.append({"type": "long_digits", "original": token, "span": m.span()})

	return InspectionResult(False, None, redacted, redactions)


__all__ = ["inspect", "InspectionResult"]

