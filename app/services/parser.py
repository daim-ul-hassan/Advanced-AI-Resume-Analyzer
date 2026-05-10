from __future__ import annotations

from pathlib import Path

from docx import Document
from pypdf import PdfReader


ALLOWED_SUFFIXES = {".pdf", ".docx", ".txt"}


def extract_resume_text(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise ValueError("Unsupported file type. Please upload PDF, DOCX, or TXT.")

    if suffix == ".pdf":
        return _extract_pdf(file_path)
    if suffix == ".docx":
        return _extract_docx(file_path)
    return file_path.read_text(encoding="utf-8", errors="ignore")


def _extract_pdf(file_path: Path) -> str:
    reader = PdfReader(str(file_path))
    pages = [(page.extract_text() or "").strip() for page in reader.pages]
    return "\n".join(page for page in pages if page).strip()


def _extract_docx(file_path: Path) -> str:
    document = Document(str(file_path))
    paragraphs = [paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip()]
    return "\n".join(paragraphs).strip()
