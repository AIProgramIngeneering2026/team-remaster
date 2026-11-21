import pytest

from remaster.domain import InvalidTransition, Job, JobError, JobStatus


def _processing_job() -> Job:
    job = Job(id="job-1")
    job.queue()
    job.start()
    return job


def test_job_reaches_processed_with_result() -> None:
    job = Job(id="job-1")

    job.queue()
    job.start()
    job.complete({"text": "hello"})

    assert job.status is JobStatus.PROCESSED
    assert job.result == {"text": "hello"}
    assert job.error is None


def test_result_is_copied_when_job_completes() -> None:
    result = {"text": "hello"}
    job = _processing_job()

    job.complete(result)
    result["text"] = "changed"

    assert job.result == {"text": "hello"}


def test_document_rejection_is_terminal_and_keeps_error() -> None:
    job = Job(id="job-1")
    error = JobError("unsupported_format", "Unsupported document format")

    job.reject(error)

    assert job.status is JobStatus.REJECTED
    assert job.error == error
    with pytest.raises(InvalidTransition):
        job.queue()


def test_processor_failure_is_terminal_and_keeps_error() -> None:
    job = _processing_job()
    error = JobError("internal_error", "Processor failed")

    job.fail(error)

    assert job.status is JobStatus.FAILED
    assert job.error == error
    with pytest.raises(InvalidTransition):
        job.complete({"text": "late result"})


def test_cancel_is_allowed_before_processing_and_idempotent() -> None:
    job = Job(id="job-1")
    job.queue()

    assert job.cancel() is True
    assert job.cancel() is False
    assert job.status is JobStatus.CANCELLED


def test_cancel_is_rejected_after_processing_starts() -> None:
    job = _processing_job()

    with pytest.raises(InvalidTransition):
        job.cancel()

    assert job.status is JobStatus.PROCESSING


# Z1: a second start cannot create a second worker for the same Job.
def test_z1_rejects_double_work() -> None:
    job = _processing_job()

    with pytest.raises(InvalidTransition):
        job.start()

    assert job.status is JobStatus.PROCESSING


# Z2: a worker interrupted by a server restart is marked failed.
def test_z2_interrupted_job_does_not_remain_processing() -> None:
    job = _processing_job()

    job.fail(JobError("interrupted", "Service restarted during processing"))

    assert job.status is JobStatus.FAILED
    assert job.error is not None
    assert job.error.code == "interrupted"


# Z3: a late worker result cannot revive a cancelled Job.
def test_z3_rejects_result_after_cancellation() -> None:
    job = Job(id="job-1")
    job.queue()
    job.cancel()

    with pytest.raises(InvalidTransition):
        job.complete({"text": "late result"})

    assert job.status is JobStatus.CANCELLED


# Z4: a failed Job cannot later become successful.
def test_z4_rejects_success_after_failure() -> None:
    job = _processing_job()
    job.fail(JobError("internal_error", "Processor failed"))

    with pytest.raises(InvalidTransition):
        job.complete({"text": "second outcome"})

    assert job.status is JobStatus.FAILED


# Z5: a Job cannot succeed before a worker has started.
def test_z5_rejects_success_without_processing() -> None:
    job = Job(id="job-1")

    with pytest.raises(InvalidTransition):
        job.complete({"text": "impossible result"})

    assert job.status is JobStatus.UPLOADED


# Z6: a successful Job cannot be run again.
def test_z6_rejects_restart_after_success() -> None:
    job = _processing_job()
    job.complete({"text": "hello"})

    with pytest.raises(InvalidTransition):
        job.start()

    assert job.status is JobStatus.PROCESSED
