"""Output guard helpers: schema validation and RAG numeric-checking.

This lightweight implementation validates that the final response can be
parsed by the declared Pydantic model and performs simple numeric-claim
cross-checking for RAG answers by looking for numeric tokens in the
answer text and checking they appear verbatim in at least one retrieved
chunk's text.

On schema parse failure this module supports a single retry via a caller
provided `regenerate` callback which should return a replacement string
for the LLM output when applicable.
"""

import re
from typing import Any, Callable, Iterable

from pydantic import ValidationError


def validate_schema(obj: Any, model_cls: Any, regenerate: Callable[[], Any] | None = None) -> Any:
	"""Ensure `obj` can be parsed into `model_cls`.

	If parsing fails and `regenerate` is provided, call it once and retry.
	Raises ValidationError on final failure.
	"""
	try:
		return model_cls.parse_obj(obj)
	except ValidationError:
		if regenerate is None:
			raise
		# attempt one retry
		regenerated = regenerate()
		try:
			return model_cls.parse_obj(regenerated)
		except ValidationError:
			raise


def _extract_numbers(text: str) -> list[str]:
	return re.findall(r"\b\d+(?:\.\d+)?\b", text)


def check_numeric_claims(answer_text: str, retrieved_texts: Iterable[str]) -> list[dict]:
	"""Return list of numeric-claim mismatches.

	For each numeric token found in the answer_text, verify the exact
	token occurs verbatim in one of the retrieved_texts. If not, return
	an entry describing the mismatch.
	"""
	nums = _extract_numbers(answer_text)
	if not nums:
		return []
	retrieved_join = "\n".join(retrieved_texts or [])
	mismatches: list[dict] = []
	for n in nums:
		if n not in retrieved_join:
			mismatches.append({"number": n, "reason": "not found in retrieved evidence"})
	return mismatches


__all__ = ["validate_schema", "check_numeric_claims"]

