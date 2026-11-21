"""Text extraction processor for PDF, DOCX, and UTF-8 text documents."""

from typing import Any

from remaster.processors.contracts import Document, InvalidParams, ProcessingResult
from remaster.processors.text_reader import DocumentParseError, extract_document_text


class TextExtractor:
    name = "extract_text"

    def validate_params(self, params: dict[str, Any]) -> None:
        if not isinstance(params, dict):
            raise InvalidParams("params", "params must be an object")
        if params:
            raise InvalidParams("params", "extract_text takes no params")

    def run(self, document: Document, params: dict[str, Any]) -> ProcessingResult:
        try:
            text = extract_document_text(document)
        except DocumentParseError:
            return ProcessingResult(
                ok=False,
                error_code="parse_error",
                error_message="Document could not be parsed",
            )
        return ProcessingResult(ok=True, data={"text": text})
