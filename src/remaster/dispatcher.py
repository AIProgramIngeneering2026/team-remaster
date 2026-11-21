"""Framework-independent execution orchestration for processing Jobs."""

from typing import Any

from remaster.domain import InvalidTransition, Job, JobError
from remaster.processors.contracts import Document, ProcessingResult
from remaster.processors.registry import ProcessorRegistry


class Dispatcher:
    """Execute an operation through the registry and apply its outcome to a Job."""

    def __init__(self, registry: ProcessorRegistry) -> None:
        self._registry = registry

    def dispatch(
        self,
        job: Job,
        operation: str,
        document: Document,
        params: dict[str, Any],
    ) -> Job:
        """Run one registered processor for a queued Job and return its new state.

        Parameter validation is a caller responsibility, as specified by the
        API contract: the API validates with the selected processor before it
        creates a Job.
        """
        processor = self._registry.get(operation)
        job.start()

        try:
            outcome = processor.run(document, params)
        except Exception:
            self._fail_if_active(job, JobError("internal_error", "Processor failed unexpectedly"))
            return job

        if not isinstance(outcome, ProcessingResult):
            self._fail_if_active(job, JobError("internal_error", "Processor returned an invalid result"))
            return job

        if outcome.ok:
            try:
                job.complete(outcome.data)
            except InvalidTransition:
                # A late result must not revive a Job that was cancelled or
                # otherwise moved to a terminal state while the tool ran.
                pass
            except (TypeError, ValueError):
                self._fail_if_active(job, JobError("internal_error", "Processor returned an invalid result"))
        else:
            code = outcome.error_code or "internal_error"
            message = outcome.error_message or "Processor failed"
            self._fail_if_active(job, JobError(code, message))

        return job

    @staticmethod
    def _fail_if_active(job: Job, error: JobError) -> None:
        try:
            job.fail(error)
        except InvalidTransition:
            # Preserve a concurrent cancellation or terminal outcome.
            pass
