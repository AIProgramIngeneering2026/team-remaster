from typing import Any

import pytest

from remaster.dispatcher import Dispatcher
from remaster.domain import InvalidTransition, Job, JobError, JobStatus
from remaster.processors import (
    Document,
    ProcessingResult,
    ProcessorRegistry,
    TextExtractor,
    UnknownOperation,
)


class StubProcessor:
    name = "stub"

    def __init__(self, outcome: ProcessingResult | Exception) -> None:
        self.outcome = outcome
        self.calls = 0

    def validate_params(self, params: dict[str, Any]) -> None:
        return None

    def run(self, document: Document, params: dict[str, Any]) -> ProcessingResult:
        self.calls += 1
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


def _queued_job() -> Job:
    job = Job(id="job-1")
    job.queue()
    return job


def _document(path: str = "unused.txt") -> Document:
    return Document(id="doc-1", path=path, format="txt", size_bytes=0)


def test_dispatcher_runs_registered_processor_and_completes_job(tmp_path) -> None:
    document_path = tmp_path / "source.txt"
    document_path.write_text("hello", encoding="utf-8")
    processor = TextExtractor()
    dispatcher = Dispatcher(ProcessorRegistry([processor]))
    job = _queued_job()

    dispatcher.dispatch(
        job,
        "extract_text",
        Document(id="doc-1", path=str(document_path), format="txt", size_bytes=5),
        {},
    )

    assert job.status is JobStatus.PROCESSED
    assert job.result == {"text": "hello"}


def test_dispatcher_maps_processor_error_to_failed_job() -> None:
    processor = StubProcessor(
        ProcessingResult(ok=False, error_code="parse_error", error_message="Bad document")
    )
    dispatcher = Dispatcher(ProcessorRegistry([processor]))
    job = _queued_job()

    dispatcher.dispatch(job, "stub", _document(), {})

    assert job.status is JobStatus.FAILED
    assert job.error == JobError("parse_error", "Bad document")


def test_dispatcher_maps_unexpected_exception_to_safe_internal_error() -> None:
    processor = StubProcessor(RuntimeError("private file path should not leak"))
    dispatcher = Dispatcher(ProcessorRegistry([processor]))
    job = _queued_job()

    dispatcher.dispatch(job, "stub", _document(), {})

    assert job.status is JobStatus.FAILED
    assert job.error == JobError("internal_error", "Processor failed unexpectedly")


def test_unknown_operation_leaves_queued_job_unchanged() -> None:
    dispatcher = Dispatcher(ProcessorRegistry())
    job = _queued_job()

    with pytest.raises(UnknownOperation):
        dispatcher.dispatch(job, "missing", _document(), {})

    assert job.status is JobStatus.QUEUED


def test_dispatcher_requires_a_queued_job() -> None:
    processor = StubProcessor(ProcessingResult(ok=True, data={}))
    dispatcher = Dispatcher(ProcessorRegistry([processor]))
    job = Job(id="job-1")

    with pytest.raises(InvalidTransition):
        dispatcher.dispatch(job, "stub", _document(), {})

    assert processor.calls == 0
    assert job.status is JobStatus.UPLOADED
