"""Operation-name based registry for processors."""

from collections.abc import Iterable

from remaster.processors.contracts import Processor


class UnknownOperation(LookupError):
    """Raised when a client requests an operation that is not registered."""

    code = "unknown_operation"

    def __init__(self, operation: str) -> None:
        self.operation = operation
        super().__init__(f"Unknown operation: {operation}")


class DuplicateOperation(ValueError):
    """Raised when a second processor tries to claim an existing operation."""


def _processor_name(processor: Processor) -> str:
    name = getattr(processor, "name", None)
    if not isinstance(name, str) or not name.strip():
        raise ValueError("A processor must have a non-empty name")
    if not callable(getattr(processor, "validate_params", None)):
        raise TypeError("A processor must implement validate_params(params)")
    if not callable(getattr(processor, "run", None)):
        raise TypeError("A processor must implement run(document, params)")
    return name


class ProcessorRegistry:
    """Register processors and resolve them without coupling callers to classes."""

    def __init__(self, processors: Iterable[Processor] = ()) -> None:
        self._processors: dict[str, Processor] = {}
        for processor in processors:
            self.register(processor)

    def register(self, processor: Processor) -> None:
        name = _processor_name(processor)
        if name in self._processors:
            raise DuplicateOperation(f"Operation already registered: {name}")
        self._processors[name] = processor

    def get(self, operation: str) -> Processor:
        try:
            return self._processors[operation]
        except KeyError as error:
            raise UnknownOperation(operation) from error

    @property
    def operations(self) -> frozenset[str]:
        return frozenset(self._processors)
