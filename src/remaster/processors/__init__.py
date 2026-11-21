"""Processor contracts, registry, and first built-in processors."""

from remaster.processors.contracts import Document, InvalidParams, ProcessingResult, Processor
from remaster.processors.registry import DuplicateOperation, ProcessorRegistry, UnknownOperation
from remaster.processors.stats import StatsProcessor
from remaster.processors.text_extractor import TextExtractor

__all__ = [
    "Document",
    "DuplicateOperation",
    "InvalidParams",
    "ProcessingResult",
    "Processor",
    "ProcessorRegistry",
    "StatsProcessor",
    "TextExtractor",
    "UnknownOperation",
]
