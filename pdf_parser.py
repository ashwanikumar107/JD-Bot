"""
core/pdf_parser.py – Extract and clean text from PDFs
"""

import re
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract text from a PDF file using pdfplumber (primary) 
    with pypdf as fallback.
    
    Returns:
        Cleaned text string, or empty string on failure.
    """
    text = ""

    # ── Primary: pdfplumber ───────────────────────────────────────────────────
    try:
        import pdfplumber
        with pdfplumber.open(file_path) as pdf:
            pages_text = []
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    pages_text.append(page_text)
            text = "\n".join(pages_text)
        if text.strip():
            logger.info(f"pdfplumber extracted {len(text)} chars from {file_path}")
            return clean_text(text)
    except Exception as e:
        logger.warning(f"pdfplumber failed for {file_path}: {e}")

    # ── Fallback: pypdf ───────────────────────────────────────────────────────
    try:
        from pypdf import PdfReader
        reader = PdfReader(file_path)
        pages_text = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                pages_text.append(page_text)
        text = "\n".join(pages_text)
        logger.info(f"pypdf extracted {len(text)} chars from {file_path}")
        return clean_text(text)
    except Exception as e:
        logger.error(f"pypdf also failed for {file_path}: {e}")

    return ""


def clean_text(text: str) -> str:
    """
    Clean extracted PDF text:
    - Normalize whitespace
    - Remove non-printable characters
    - Collapse multiple blank lines
    """
    # Remove non-printable except newlines/tabs
    text = re.sub(r"[^\x20-\x7E\n\t]", " ", text)
    # Collapse multiple spaces
    text = re.sub(r" {2,}", " ", text)
    # Collapse multiple blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_sections(text: str) -> dict:
    """
    Attempt to extract common resume sections.
    Returns a dict of {section_name: content}.
    """
    section_patterns = {
        "contact": r"(?i)(contact|personal info|personal information)",
        "summary": r"(?i)(summary|objective|profile|about me)",
        "experience": r"(?i)(experience|work experience|employment|work history|professional experience)",
        "education": r"(?i)(education|academic|qualifications|degrees)",
        "skills": r"(?i)(skills|technical skills|competencies|expertise|technologies)",
        "projects": r"(?i)(projects|portfolio|key projects)",
        "certifications": r"(?i)(certifications|certificates|licenses)",
        "achievements": r"(?i)(achievements|awards|honors|accomplishments)",
    }

    lines = text.split("\n")
    sections: dict = {}
    current_section = "header"
    buffer = []

    for line in lines:
        line_stripped = line.strip()
        matched_section = None

        for sec_name, pattern in section_patterns.items():
            if re.match(pattern, line_stripped):
                matched_section = sec_name
                break

        if matched_section:
            # Save previous buffer
            if buffer:
                sections[current_section] = "\n".join(buffer).strip()
            current_section = matched_section
            buffer = []
        else:
            if line_stripped:
                buffer.append(line_stripped)

    # Save last section
    if buffer:
        sections[current_section] = "\n".join(buffer).strip()

    return sections


def get_word_count(text: str) -> int:
    return len(text.split())
