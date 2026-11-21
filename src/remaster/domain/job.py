"""Domain model and lifecycle rules for a processing job."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, ClassVar
from uuid import uuid4


class JobStatus(StrEnum):
    UPLOADED = "uploaded"
    QUEUED = "queued"
    PROCESSING = "processing"
    PROCESSED = "processed"
    REJECTED = "rejected"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class JobError:
    """A stable error code and human-readable explanation stored on a Job."""

    code: str
    message: str


class InvalidTransition(Exception):
    """Raised when a command tries to move a Job along a forbidden edge."""

    code = "invalid_transition"

    def __init__(self, current: JobStatus, target: JobStatus) -> None:
        self.current = current
        self.target = target
        super().__init__(f"Cannot transition Job from {current.value} to {target.value}")


@dataclass(slots=True)
class Job:
    """A Job whose state can only change through validated domain operations."""

    id: str = field(default_factory=lambda: str(uuid4()))
    _status: JobStatus = field(default=JobStatus.UPLOADED, init=False, repr=False)
    _result: dict[str, Any] | None = field(default=None, init=False, repr=False)
    _error: JobError | None = field(default=None, init=False, repr=False)

    _ALLOWED_TRANSITIONS: ClassVar[dict[JobStatus, frozenset[JobStatus]]] = {
        JobStatus.UPLOADED: frozenset({JobStatus.QUEUED, JobStatus.REJECTED, JobStatus.CANCELLED}),
        JobStatus.QUEUED: frozenset({JobStatus.PROCESSING, JobStatus.CANCELLED}),
        JobStatus.PROCESSING: frozenset({JobStatus.PROCESSED, JobStatus.FAILED}),
        JobStatus.PROCESSED: frozenset(),
        JobStatus.REJECTED: frozenset(),
        JobStatus.FAILED: frozenset(),
        JobStatus.CANCELLED: frozenset(),
    }

    @property
    def status(self) -> JobStatus:
        return self._status

    @property
    def result(self) -> dict[str, Any] | None:
        return None if self._result is None else dict(self._result)

    @property
    def error(self) -> JobError | None:
        return self._error

    def queue(self) -> None:
        self._transition_to(JobStatus.QUEUED)

    def reject(self, error: JobError) -> None:
        self._transition_to(JobStatus.REJECTED, error=error)

    def start(self) -> None:
        self._transition_to(JobStatus.PROCESSING)

    def complete(self, result: Mapping[str, Any]) -> None:
        if result is None:
            raise ValueError("A processed Job must have a result")
        copied_result = dict(result)
        self._transition_to(JobStatus.PROCESSED, result=copied_result)

    def fail(self, error: JobError) -> None:
        self._transition_to(JobStatus.FAILED, error=error)

    def cancel(self) -> bool:
        """Cancel before processing; repeated cancellation is an idempotent no-op."""
        if self._status is JobStatus.CANCELLED:
            return False
        self._transition_to(JobStatus.CANCELLED)
        return True

    def _transition_to(
        self,
        target: JobStatus,
        *,
        result: dict[str, Any] | None = None,
        error: JobError | None = None,
    ) -> None:
        if target not in self._ALLOWED_TRANSITIONS[self._status]:
            raise InvalidTransition(self._status, target)

        if target is JobStatus.PROCESSED and result is None:
            raise ValueError("A processed Job must have a result")
        if target in {JobStatus.REJECTED, JobStatus.FAILED} and error is None:
            raise ValueError(f"A {target.value} Job must have an error")

        self._status = target
        self._result = result
        self._error = error
