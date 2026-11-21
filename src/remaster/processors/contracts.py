"""Shared processor contract defined by docs/tool-contract.md."""

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class Document:
    id: str
    path: str
    format: str
    size_bytes: int


@dataclass(frozen=True, slots=True)
class ProcessingResult:
    ok: bool
    data: dict[str, Any] = field(default_factory=dict)
    error_code: str | None = None
    error_message: str | None = None


class InvalidParams(Exception):
    """Raised for invalid processor parameters; field names the bad input."""

    code = "invalid_params"

    def __init__(self, field: str, message: str) -> None:
        super().__init__(message)
        self.field = field
        self.message = message


class Processor(Protocol):
    name: str

    def validate_params(self, params: dict[str, Any]) -> None:
        """Raise InvalidParams for invalid input."""

    def run(self, document: Document, params: dict[str, Any]) -> ProcessingResult:
        """Execute the operation and return its outcome."""
