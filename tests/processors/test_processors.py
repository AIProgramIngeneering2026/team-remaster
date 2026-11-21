from pathlib import Path
from typing import Any

import pytest
from docx import Document as DocxWriter
from pypdf import PdfWriter

from remaster.processors import Document, InvalidParams, StatsProcessor, TextExtractor


def _document(path: Path, file_format: str) -> Document:
    return Document(id="doc-1", path=str(path), format=file_format, size_bytes=path.stat().st_size)


def test_text_extractor_reads_utf8_text(tmp_path: Path) -> None:
    path = tmp_path / "source.txt"
    path.write_text("Привет, Remaster!", encoding="utf-8")

    result = TextExtractor().run(_document(path, "txt"), {})

    assert result.ok is True
    assert result.data == {"text": "Привет, Remaster!"}


def test_text_extractor_reads_docx_paragraphs(tmp_path: Path) -> None:
    path = tmp_path / "source.docx"
    source = DocxWriter()
    source.add_paragraph("first paragraph")
    source.add_paragraph("second paragraph")
    source.save(path)

    result = TextExtractor().run(_document(path, "docx"), {})

    assert result.ok is True
    assert result.data == {"text": "first paragraph\n\nsecond paragraph"}


def test_text_extractor_reads_pdf_pages(tmp_path: Path) -> None:
    path = tmp_path / "source.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    with path.open("wb") as file:
        writer.write(file)

    result = TextExtractor().run(_document(path, "pdf"), {})

    assert result.ok is True
    assert result.data == {"text": ""}


def test_text_extractor_returns_parse_error_for_missing_file(tmp_path: Path) -> None:
    document = Document(
        id="doc-1",
        path=str(tmp_path / "missing.txt"),
        format="txt",
        size_bytes=0,
    )

    result = TextExtractor().run(document, {})

    assert result.ok is False
    assert result.error_code == "parse_error"
    assert "missing.txt" not in (result.error_message or "")


def test_stats_processor_counts_text_and_top_words(tmp_path: Path) -> None:
    path = tmp_path / "source.txt"
    text = "Hello, world!\n\nHello Remaster."
    path.write_text(text, encoding="utf-8")

    result = StatsProcessor().run(_document(path, "txt"), {})

    assert result.ok is True
    assert result.data == {
        "words": 4,
        "chars": len(text),
        "paragraphs": 2,
        "top_words": [["hello", 2], ["world", 1], ["remaster", 1]],
    }


def test_stats_processor_returns_zeroes_for_empty_document(tmp_path: Path) -> None:
    path = tmp_path / "empty.txt"
    path.write_text("", encoding="utf-8")

    result = StatsProcessor().run(_document(path, "txt"), {})

    assert result.ok is True
    assert result.data == {"words": 0, "chars": 0, "paragraphs": 0, "top_words": []}


@pytest.mark.parametrize("processor", [TextExtractor(), StatsProcessor()])
def test_processors_reject_unexpected_params(processor: Any) -> None:
    with pytest.raises(InvalidParams) as error:
        processor.validate_params({"unexpected": True})

    assert error.value.code == "invalid_params"
    assert error.value.field == "params"


@pytest.mark.parametrize("processor", [TextExtractor(), StatsProcessor()])
def test_processors_accept_empty_params(processor: Any) -> None:
    processor.validate_params({})
