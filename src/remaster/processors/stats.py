"""Document statistics processor."""

import re
from collections import Counter
from typing import Any

from remaster.processors.contracts import Document, InvalidParams, ProcessingResult
from remaster.processors.text_reader import DocumentParseError, extract_document_text

_WORD_PATTERN = re.compile(r"\w+", flags=re.UNICODE)
_PARAGRAPH_SEPARATOR = re.compile(r"\n\s*\n")


class StatsProcessor:
    name = "stats"

    def validate_params(self, params: dict[str, Any]) -> None:
        if not isinstance(params, dict):
            raise InvalidParams("params", "params must be an object")
        if params:
            raise InvalidParams("params", "stats takes no params")

    def run(self, document: Document, params: dict[str, Any]) -> ProcessingResult:
        try:
            text = extract_document_text(document)
        except DocumentParseError:
            return ProcessingResult(
                ok=False,
                error_code="parse_error",
                error_message="Document could not be parsed",
            )

        words = [word.casefold() for word in _WORD_PATTERN.findall(text)]
        paragraphs = [part for part in _PARAGRAPH_SEPARATOR.split(text.strip()) if part.strip()]
        top_words = [[word, count] for word, count in Counter(words).most_common(10)]

        return ProcessingResult(
            ok=True,
            data={
                "words": len(words),
                "chars": len(text),
                "paragraphs": len(paragraphs),
                "top_words": top_words,
            },
        )
