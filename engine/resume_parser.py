
"""Extract resume text from PDF and organize it into sections."""

from __future__ import annotations

import re
import unicodedata
from io import BytesIO
from pathlib import Path
from typing import Any

from pypdf import PdfReader


# Internal section names are kept stable where possible for compatibility
# with the existing resume scanner.
SECTION_ALIASES = {
    "professional_summary": [
        "summary",
        "professional summary",
        "profile",
        "career objective",
        "objective",
        "about me",
        "professional profile",
    ],
    "skills": [
        "skills",
        "technical skills",
        "core skills",
        "key skills",
        "technical competencies",
        "core competencies",
        "tech stack",
        "technology stack",
        "technologies",
        "tools",
        "programming skills",
    ],
    "experience": [
        "experience",
        "experiences",
        "work experience",
        "work experiences",
        "professional experience",
        "professional experiences",
        "employment history",
        "work history",
        "career history",
    ],
    "internships": [
        "internship",
        "internships",
        "internship experience",
        "internship experiences",
    ],
    "projects": [
        "projects",
        "personal projects",
        "academic projects",
        "project experience",
        "key projects",
        "selected projects",
    ],
    "education": [
        "education",
        "academic background",
        "educational qualifications",
        "academic qualifications",
        "qualification",
        "qualifications",
    ],
    "certifications": [
        "certifications",
        "certificates",
        "licenses",
        "licences",
        "courses",
        "training",
        "courses and certifications",
    ],
    "achievements": [
        "achievements",
        "accomplishments",
        "honors",
        "honours",
        "recognition",
        "scholarships",
    ],
    "awards": [
        "awards",
        "awards and achievements",
        "honors and awards",
        "honours and awards",
    ],
    "contributions": [
        "contributions",
        "open source",
        "open source contributions",
        "community contributions",
    ],
    "publications": [
        "publications",
        "research",
        "research papers",
        "papers",
        "patents",
    ],
    "activities": [
        "activities",
        "extracurricular",
        "extracurricular activities",
        "volunteering",
        "volunteer experience",
        "volunteer work",
        "leadership",
        "leadership experience",
        "positions of responsibility",
        "responsibilities",
        "clubs",
        "strengths"
    ],
    "languages": [
        "languages",
        "language",
        "language proficiency",
    ],
    "interests": [
        "interests",
        "hobbies",
        "interests and hobbies",
    ],
    "personal_details": [
        "personal details",
        "personal information",
    ],
    "references": [
        "references",
        "declaration",
    ],
}

# Sections that should not be stored or scanned as skill evidence.
IGNORED_SECTIONS = {
    "personal_details",
    "references",
}

# Build a normalized lookup once instead of checking every alias repeatedly.
HEADING_LOOKUP = {
    alias: section
    for section, aliases in SECTION_ALIASES.items()
    for alias in aliases
}

BULLET_PREFIX = re.compile(r"^\s*(?:[-*•▪◦‣]|\d+[.)])\s+")


def _strip_heading_decoration(line: str) -> str:
    """Remove common Markdown and decorative heading characters."""

    line = line.strip()

    # Markdown heading prefix.
    line = re.sub(r"^#{1,6}\s*", "", line)

    # Bold, italic, and inline-code markers.
    line = re.sub(r"[*_`~]", "", line)

    # Remove leading icons/symbols while retaining letters and numbers.
    while line and unicodedata.category(line[0]).startswith(("S", "C")):
        line = line[1:].lstrip()

    return line.strip()


def _normalize_heading(line: str) -> str:
    """Normalize a possible section heading for exact comparison."""

    line = _strip_heading_decoration(line)
    line = line.strip(" |•▪◦-\t")
    line = re.sub(r"\s+", " ", line)
    line = line.rstrip(":").strip()

    return line.lower()


def _find_section_heading(line: str) -> str | None:
    """Return the canonical section name for a recognized heading."""

    # A bullet that happens to contain a heading word is not a heading.
    if BULLET_PREFIX.match(line):
        return None

    normalized = _normalize_heading(line)
    return HEADING_LOOKUP.get(normalized)



def _looks_like_unknown_heading(line: str) -> bool:
    """Detect unfamiliar headings conservatively."""

    if not line or BULLET_PREFIX.match(line):
        return False

    original = line.strip()

    if len(original) > 55:
        return False

    candidate = _strip_heading_decoration(original).rstrip(":").strip()

    if not candidate:
        return False

    # A trailing colon is a strong heading signal.
    if original.endswith(":"):
        return True

    # Recognize ALL-CAPS headings such as OPEN SOURCE or STRENGTHS.
    letters = [char for char in candidate if char.isalpha()]

    if letters and all(char.isupper() for char in letters):
        return True

    # Ordinary title-case lines are ambiguous:
    # "Test User", "Python Programming Certificate", etc.
    return False


def _unknown_heading_key(line: str) -> str:
    """Convert an unknown heading into a stable dictionary key."""

    normalized = _normalize_heading(line)
    key = re.sub(r"[^a-z0-9]+", "_", normalized)
    return key.strip("_") or "unnamed_section"


def _extract_contact(
    line: str,
    personal_info: dict[str, Any],
) -> str:
    """Extract contact details and return the remaining line."""

    email_match = re.search(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        line,
    )

    phone_match = re.search(
        r"(?<!\w)\+?\d[\d\s().-]{7,}\d(?!\w)",
        line,
    )

    if email_match:
        personal_info["email"] = email_match.group(0)
        line = line.replace(email_match.group(0), "")

    if phone_match:
        personal_info["phone"] = phone_match.group(0).strip()
        line = line.replace(phone_match.group(0), "")

    return line.strip(" |,-\t")


def _extract_name(header_lines: list[str]) -> str:
    """Find a likely name from the resume header."""

    for line in header_lines:
        candidate = re.sub(
            r"https?://\S+|www\.\S+",
            "",
            line,
            flags=re.IGNORECASE,
        ).strip(" |,-\t")

        words = candidate.split()

        if (
            2 <= len(words) <= 5
            and not re.search(r"@", candidate)
            and not re.search(r"\d", candidate)
            and not re.search(
                r"\b(linkedin|github|portfolio|www)\b",
                candidate,
                flags=re.IGNORECASE,
            )
        ):
            return candidate

    return ""


def _new_section_storage() -> dict[str, Any]:
    """Create the section storage structure."""

    return {
        "professional_summary": [],
        "skills": [],
        "experience": [],
        "internships": [],
        "projects": [],
        "education": [],
        "certifications": [],
        "achievements": [],
        "awards": [],
        "contributions": [],
        "publications": [],
        "activities": [],
        "languages": [],
        "interests": [],
        "other": {},
    }


def _clean_sections(sections: dict[str, Any]) -> dict[str, Any]:
    """Join collected lines and remove empty sections."""

    cleaned: dict[str, Any] = {}

    for section, content in sections.items():
        if section == "other":
            other_sections = {
                heading: "\n".join(lines).strip()
                for heading, lines in content.items()
                if lines and "\n".join(lines).strip()
            }

            if other_sections:
                cleaned["other"] = other_sections

        elif isinstance(content, list):
            value = "\n".join(content).strip()

            if value:
                cleaned[section] = value

    return cleaned


def extract_pdf_text(pdf_path: str | Path) -> str:
    """Extract text from a PDF file."""

    path = Path(pdf_path)

    if not path.exists():
        raise FileNotFoundError(f"Resume file not found: {path}")

    if path.suffix.lower() != ".pdf":
        raise ValueError("Only PDF resume files are supported.")

    reader = PdfReader(str(path))
    pages = [page.extract_text() or "" for page in reader.pages]
    text = "\n".join(pages).strip()

    if not text:
        raise ValueError(
            "No readable text found in PDF. "
            "The file may be scanned or image-based."
        )

    return text


def parse_resume_text(text: str) -> dict[str, Any]:
    """Split extracted resume text into recognized and unknown sections."""

    if not text or not text.strip():
        raise ValueError("Resume text cannot be empty.")

    sections = _new_section_storage()

    personal_info: dict[str, Any] = {
        "name": "",
        "email": "",
        "phone": "",
    }

    header_lines: list[str] = []

    current_section: str | None = None
    current_unknown_heading: str | None = None

    lines = text.splitlines()

    for raw_line in lines:
        line = raw_line.strip()

        if not line:
            continue

        # Ignore decorative underline/separator lines.
        if re.fullmatch(r"[-_=~.]{3,}", line):
            continue

        # Try known headings first.
        heading = _find_section_heading(line)

        if heading:
            current_section = heading
            current_unknown_heading = None
            continue

        # Preserve unfamiliar headings in sections["other"].
            # Do not mistake an ALL-CAPS name in the resume header for a heading.
        is_header_name = (
    current_section is None
    and 2 <= len(line.split()) <= 5
    and line.isupper()
    and not re.search(r"\d|@", line)
)

# Preserve unfamiliar headings in sections["other"].
        if not is_header_name and _looks_like_unknown_heading(line):
            unknown_key = _unknown_heading_key(line)

            current_section = "other"
            current_unknown_heading = unknown_key

            sections["other"].setdefault(unknown_key, [])
            continue

        # Extract contact details wherever they appear.
        line = _extract_contact(line, personal_info)

        if not line:
            continue

        # Content before the first recognized/unknown heading belongs
        # to the resume header, not to an arbitrary "other" section.
        if current_section is None:
            header_lines.append(line)
            continue

        # Ignore personal details and reference sections.
        if current_section in IGNORED_SECTIONS:
            continue

        if current_section == "other":
            if current_unknown_heading:
                sections["other"][current_unknown_heading].append(line)
            continue

        sections[current_section].append(line)

    personal_info["name"] = _extract_name(header_lines)

    # Keep useful header details such as LinkedIn/GitHub URLs.
    # Store them under "other" so the existing output still preserves them.
    header_details = [
        line
        for line in header_lines
        if line != personal_info["name"]
    ]

    if header_details:
        sections["other"]["header"] = header_details

    cleaned_sections = _clean_sections(sections)

    return {
        "personal_info": personal_info,
        "sections": cleaned_sections,
    }


def parse_resume_pdf(pdf_path: str | Path) -> dict[str, Any]:
    """Extract and parse a PDF resume."""

    text = extract_pdf_text(pdf_path)
    return parse_resume_text(text)


def parse_resume_pdf_bytes(pdf_bytes: bytes) -> dict[str, Any]:
    """Parse a PDF resume directly from uploaded bytes."""

    if not pdf_bytes:
        raise ValueError("Uploaded PDF is empty.")

    reader = PdfReader(BytesIO(pdf_bytes))

    text = "\n".join(
        page.extract_text() or ""
        for page in reader.pages
    )

    if not text.strip():
        raise ValueError(
            "No readable text found in PDF. "
            "The file may be scanned or image-based."
        )

    return parse_resume_text(text)
