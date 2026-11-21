"""Remaster document processing service."""

from remaster.dispatcher import Dispatcher
from remaster.domain import InvalidTransition, Job, JobError, JobStatus
from remaster.processors import (
    Document,
    InvalidParams,
    ProcessingResult,
    Processor,
    ProcessorRegistry,
    StatsProcessor,
    TextExtractor,
    UnknownOperation,
)

__all__ = [
    "Dispatcher",
    "Document",
    "InvalidParams",
    "InvalidTransition",
    "Job",
    "JobError",
    "JobStatus",
    "ProcessingResult",
    "Processor",
    "ProcessorRegistry",
    "StatsProcessor",
    "TextExtractor",
    "UnknownOperation",
]
