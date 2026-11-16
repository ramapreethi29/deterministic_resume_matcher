
"""Full-text resume skill scanner with section-level evidence."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from .normalize import canon, find_skills, skill_type


SOURCE_ALIASES = {
    "professional_summary": "summary",
    "profile": "summary",
    "technical_skills": "skills",
    "core_skills": "skills",
    "key_skills": "skills",
    "work_experience": "experience",
    "work_experiences": "experience",
    "professional_experience": "experience",
    "professional_experiences": "experience",
    "internship": "experience",
    "internships": "experience",
    "internship_experience": "experience",
    "personal_projects": "projects",
    "academic_projects": "projects",
    "certificates": "certifications",
    "accomplishments": "achievements",
}

SOURCE_ORDER = [
    "experience",
    "projects",
    "skills",
    "summary",
    "certifications",
    "education",
    "achievements",
    "awards",
    "contributions",
    "publications",
    "activities",
    "other",
]

DEMONSTRATED_SOURCES = {"experience", "projects"}
MENTIONED_SOURCES = {"summary", "certifications", "education"}


def _flatten(value: Any) -> str:
    """Convert nested resume content into searchable text."""

    if value is None:
        return ""

    if isinstance(value, dict):
        return " ".join(_flatten(v) for v in value.values())

    if isinstance(value, (list, tuple, set)):
        return "\n".join(_flatten(v) for v in value)

    return str(value).strip()


def _normalize_source(source: str) -> str:
    """Normalize a section name to its standard evidence label."""

    normalized = re.sub(
        r"[\s-]+",
        "_",
        str(source).lower().strip(),
    )

    return SOURCE_ALIASES.get(normalized, normalized)


def _add_evidence(
    evidence: dict[str, set[str]],
    skill: str,
    source: str,
) -> None:
    """Add a canonical skill and its normalized evidence source."""

    canonical = canon(skill)
    normalized_source = _normalize_source(source)

    if canonical and normalized_source:
        evidence[canonical].add(normalized_source)


def _certification_title_text(text: str) -> str:
    """
    Keep certification titles and remove issuer/year information.

    Example:
    Introduction to Generative AI — Google Cloud Skills Boost, 2026

    Becomes:
    Introduction to Generative AI
    """

    titles: list[str] = []

    for line in text.splitlines():
        line = line.strip()

        if not line:
            continue

        # Remove issuer information after an em dash, en dash,
        # or a spaced hyphen separator.
        title = re.split(r"\s+[—–-]\s+|—", line, maxsplit=1)[0]
        title = title.strip()

        if title:
            titles.append(title)

    return "\n".join(titles)


def _education_coursework(text: str) -> str:
    """
    Extract coursework without scanning degree, college,
    branch, graduation year, or CGPA as skill evidence.
    """

    selected_lines: list[str] = []
    collecting = False

    coursework_heading = re.compile(
        r"\b(coursework|relevant coursework|relevant courses|"
        r"course subjects|subjects studied|academic subjects|courses)\b",
        re.IGNORECASE,
    )

    for line in text.splitlines():
        stripped = line.strip()

        if not stripped:
            continue

        match = coursework_heading.search(stripped)

        if match:
            collecting = True
            remainder = stripped[match.end():].strip(" :-|")

            if remainder:
                selected_lines.append(remainder)

            continue

        if collecting:
            if re.search(
                r"\b(cgpa|gpa|b\.?tech|bachelor|master|university|"
                r"college|institute|graduation)\b",
                stripped,
                re.IGNORECASE,
            ):
                collecting = False
                continue

            selected_lines.append(stripped)

    return "\n".join(selected_lines)



def _evidence_label(sources: set[str]) -> str:
    """Choose the strongest evidence level for a skill."""

    if sources & DEMONSTRATED_SOURCES:
        return "demonstrated"

    if "skills" in sources:
        return "claimed"

    return "mentioned"

def _ordered_sources(sources: set[str]) -> list[str]:
    """Return sources in a consistent, readable order."""

    known = [source for source in SOURCE_ORDER if source in sources]
    additional = sorted(sources - set(SOURCE_ORDER))

    return known + additional


def scan_resume(resume: dict[str, Any]) -> dict[str, Any]:
    """
    Scan resume sections independently and preserve skill evidence.

    Personal information and links are excluded.
    Activities are scanned for soft skills only.
    Languages and interests are retained but not scanned for skills.
    Certification issuer information is never scanned for skills.
    """

    result = dict(resume)

    sections = resume.get("sections", {})
    existing_skills = resume.get("skills", {})

    if not isinstance(sections, dict):
        sections = {}

    if not isinstance(existing_skills, dict):
        existing_skills = {}

    evidence: dict[str, set[str]] = defaultdict(set)

    # 1. Preserve existing normalized skills and their evidence.
    for category in ("technical", "soft"):
        category_skills = existing_skills.get(category, {})

        if not isinstance(category_skills, dict):
            continue

        for skill, details in category_skills.items():
            sources = (
                details.get("sources", [])
                if isinstance(details, dict)
                else []
            )

            if isinstance(sources, str):
                sources = [sources]

            if sources:
                for source in sources:
                    normalized_source = _normalize_source(str(source))

                    if normalized_source == "certifications":
                        continue

                    _add_evidence(evidence, skill, normalized_source)
            else:
                _add_evidence(evidence, skill, "skills")

    # 2. Scan each section independently.
    section_text: dict[str, str] = {}
    certifications = _flatten(sections.get("certifications", []))
    excluded_sections = {
        "personal_info",
        "personal_details",
        "links",
        "contact",
        "contact_info",
        "languages",
        "interests",
        "references",
        "declaration",
    }

    for section_name, section_value in sections.items():
        source = _normalize_source(str(section_name))

        if source in excluded_sections:
            continue

        text = _flatten(section_value)
        section_text[source] = text

        if not text:
            continue

        # Activities: retain only soft-skill matches.
        if source == "activities":
            discovered_skills = find_skills(text, section=source)

            for skill in discovered_skills:
                if skill_type(skill) == "soft":
                    _add_evidence(evidence, skill, source)

            continue

        scan_text = text

        if source == "education":
            scan_text = _education_coursework(text)

        elif source == "certifications":
            scan_text = _certification_title_text(text)

        if not scan_text:
            continue

        discovered_skills = find_skills(scan_text, section=source)

        for skill in discovered_skills:
            _add_evidence(evidence, skill, source)

    # 3. Build categorized skill dictionaries with evidence labels.
    technical: dict[str, dict[str, Any]] = {}
    soft: dict[str, dict[str, Any]] = {}

    for skill in sorted(evidence):
        sources = evidence[skill]

        entry = {
            "sources": _ordered_sources(sources),
            "evidence": _evidence_label(sources),
        }

        if skill_type(skill) == "soft":
            soft[skill] = entry
        else:
            technical[skill] = entry

    # 4. Create deduplicated skill collections.
    all_technical_skills = set(technical)
    all_soft_skills = set(soft)
    all_skills = all_technical_skills | all_soft_skills

    # 5. Preserve existing resume fields and add scanner output.
    result["skills"] = {
        "technical": technical,
        "soft": soft,
    }

    result["all_technical_skills"] = sorted(all_technical_skills)
    result["all_soft_skills"] = sorted(all_soft_skills)
    result["all_skills"] = sorted(all_skills)

    result["technical_skills"] = all_technical_skills
    result["soft_skills"] = all_soft_skills
    result["section_text"] = section_text
    result["certifications"] = (
    _flatten(sections.get("certifications", []))
    or resume.get("certifications", [])
)
    return result
