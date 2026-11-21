"""Read text from supported document files without exposing parser details."""

from pathlib import Path

from remaster.processors.contracts import Document


class DocumentParseError(Exception):
    """The file could not be decoded as the declared document format."""


def extract_document_text(document: Document) -> str:
    file_path = Path(document.path)
    file_format = document.format.lower()

    try:
        if file_format == "txt":
            return file_path.read_text(encoding="utf-8")
        if file_format == "pdf":
            from pypdf import PdfReader

            reader = PdfReader(str(file_path))
            return "\n\n".join(page.extract_text() or "" for page in reader.pages)
        if file_format == "docx":
            from docx import Document as DocxReader

            parsed = DocxReader(str(file_path))
            return "\n\n".join(paragraph.text for paragraph in parsed.paragraphs)
    except Exception as error:
        raise DocumentParseError("Could not parse document") from error

    raise DocumentParseError("Unsupported document format")
