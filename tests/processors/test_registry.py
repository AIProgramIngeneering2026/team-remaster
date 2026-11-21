from typing import Any

import pytest

from remaster.processors import DuplicateOperation, ProcessorRegistry, UnknownOperation


class StubProcessor:
    def __init__(self, name: str) -> None:
        self.name = name

    def validate_params(self, params: dict[str, Any]) -> None:
        return None

    def run(self, document: Any, params: dict[str, Any]) -> Any:
        return None


class NamedObject:
    name = "not_a_processor"


def test_registry_returns_processor_by_operation_name() -> None:
    processor = StubProcessor("extract_text")
    registry = ProcessorRegistry([processor])

    assert registry.get("extract_text") is processor
    assert registry.operations == frozenset({"extract_text"})


def test_registry_rejects_unknown_operation() -> None:
    registry = ProcessorRegistry()

    with pytest.raises(UnknownOperation) as error:
        registry.get("not_registered")

    assert error.value.code == "unknown_operation"
    assert error.value.operation == "not_registered"


def test_registry_rejects_duplicate_operation_names() -> None:
    registry = ProcessorRegistry([StubProcessor("stats")])

    with pytest.raises(DuplicateOperation):
        registry.register(StubProcessor("stats"))


def test_registry_rejects_object_without_processor_methods() -> None:
    registry = ProcessorRegistry()

    with pytest.raises(TypeError, match="validate_params"):
        registry.register(NamedObject())  # type: ignore[arg-type]
