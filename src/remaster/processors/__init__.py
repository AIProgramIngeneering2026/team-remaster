"""Processor contracts and registry."""

from remaster.processors.contracts import Document, InvalidParams, ProcessingResult, Processor
from remaster.processors.registry import DuplicateOperation, ProcessorRegistry, UnknownOperation

__all__ = [
    "Document",
    "DuplicateOperation",
    "InvalidParams",
    "ProcessingResult",
    "Processor",
    "ProcessorRegistry",
    "UnknownOperation",
]
