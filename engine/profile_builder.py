
"""Build a normalized resume profile from parsed PDF sections."""

from __future__ import annotations

import re
from datetime import date
from typing import Any

from .resume_scan import scan_resume


MONTHS = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

MONTH_PATTERN = (
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
    r"Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|"
    r"Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
)


def _get_month_year(value: str) -> tuple[int, int] | None:
    """Convert a month/year string into numeric values."""
    match = re.search(
        rf"\b({MONTH_PATTERN})\s+(\d{{4}})\b",
        value,
        re.I,
    )

    if not match:
        return None

    month = MONTHS[match.group(1).lower()]
    year = int(match.group(2))

    return year, month


def _date_ranges(text: str) -> list[tuple[str, str, int]]:
    """Extract date ranges and their duration in months."""
    pattern = (
        rf"\b({MONTH_PATTERN}\s+\d{{4}})"
        rf"\s*(?:[-–—]|to)\s*"
        rf"({MONTH_PATTERN}\s+\d{{4}}|Present|Current)\b"
    )

    results = []

    for match in re.finditer(pattern, text, re.I):
        start_text, end_text = match.groups()

        start = _get_month_year(start_text)

        if not start:
            continue

        end = _get_month_year(end_text)

        if end_text.lower() in {"present", "current"}:
            today = date.today()
            end = (today.year, today.month)

        if not end:
            continue

        start_year, start_month = start
        end_year, end_month = end

        duration = (
            (end_year - start_year) * 12
            + end_month - start_month + 1
        )

        if duration <= 0:
            continue

        results.append((
            f"{start_year:04d}-{start_month:02d}",
            f"{end_year:04d}-{end_month:02d}",
            duration,
        ))

    return results


def _clean_job_title(title: str) -> str:
    """Remove duplicated internship wording from a job title."""
    title = re.sub(r"\s+", " ", title).strip(" -|")

    # Example: Python Developer Intern Internship
    # becomes: Python Developer Intern
    if re.search(r"\bintern\b", title, re.I):
        title = re.sub(r"\s+\binternship\b", "", title, flags=re.I)

    return title.strip()


def _extract_experience(text: str) -> dict[str, Any]:
    """Extract experience records without double-counting overlapping months."""

    lines = [
        line.strip(" |")
        for line in text.splitlines()
        if line.strip()
    ]

    records = []
    professional_ranges = []
    internship_ranges = []

    def to_month(value: str) -> int:
        year, month = map(int, value.split("-"))
        return year * 12 + month - 1

    def merge_ranges(ranges: list[tuple[int, int]]) -> list[tuple[int, int]]:
        if not ranges:
            return []

        ranges = sorted(ranges)
        merged = [ranges[0]]

        for start, end in ranges[1:]:
            previous_start, previous_end = merged[-1]

            if start <= previous_end + 1:
                merged[-1] = (
                    previous_start,
                    max(previous_end, end),
                )
            else:
                merged.append((start, end))

        return merged

    def total_months(ranges: list[tuple[int, int]]) -> int:
        return sum(end - start + 1 for start, end in ranges)

    for index, line in enumerate(lines):
        ranges = _date_ranges(line)

        if not ranges:
            continue

        start, end, months = ranges[0]

        context = " ".join(lines[max(0, index - 2):index + 1])
        lower_context = context.lower()

        experience_type = (
            "internship"
            if re.search(r"\bintern(ship)?\b", lower_context)
            else "professional"
        )

        title = lines[index - 2] if index >= 2 else ""
        company = lines[index - 1] if index >= 1 else ""
        title = _clean_job_title(title)

        records.append({
            "title": title,
            "company": company,
            "start": start,
            "end": end,
            "type": experience_type,
            "months": months,
        })

        period = (to_month(start), to_month(end))

        if experience_type == "internship":
            internship_ranges.append(period)
        else:
            professional_ranges.append(period)

    professional_ranges = merge_ranges(professional_ranges)
    internship_ranges = merge_ranges(internship_ranges)

    # Remove months already counted as professional experience
    # from internship periods.
    remaining_internship = []

    for start, end in internship_ranges:
        segments = [(start, end)]

        for prof_start, prof_end in professional_ranges:
            updated = []

            for seg_start, seg_end in segments:
                if prof_end < seg_start or prof_start > seg_end:
                    updated.append((seg_start, seg_end))
                else:
                    if seg_start < prof_start:
                        updated.append((seg_start, prof_start - 1))

                    if seg_end > prof_end:
                        updated.append((prof_end + 1, seg_end))

            segments = updated

        remaining_internship.extend(segments)

    return {
        "professional_months": total_months(professional_ranges),
        "internship_months": total_months(remaining_internship),
        "records": records,
    }


def _extract_education(text: str) -> dict[str, Any]:
    """Extract degree, branch, dates, and CGPA."""
    lower = text.lower()

    degree_raw = ""
    degree_level = "none"

    # Prefer the actual degree abbreviation over generic words
    # such as Bachelor or Master.
    degree_patterns = [
        (r"\bPh\.?\s*D\.?\b", "doctorate"),
        (r"\bM\.?\s*Tech\b", "master"),
        (r"\bM\.?\s*E\.?\b", "master"),
        (r"\bM\.?\s*Sc\.?\b", "master"),
        (r"\bB\.?\s*Tech\b", "bachelor"),
        (r"\bB\.?\s*E\.?\b", "bachelor"),
        (r"\bB\.?\s*Sc\.?\b", "bachelor"),
        (r"\bdoctorate\b", "doctorate"),
        (r"\bmaster(?:'s)?\b", "master"),
        (r"\bbachelor(?:'s)?\b", "bachelor"),
        (r"\bdiploma\b", "diploma"),
        (r"\bassociate\b", "associate"),
    ]

    for pattern, level in degree_patterns:
        match = re.search(pattern, text, re.I)

        if match:
            degree_raw = re.sub(r"\s+", "", match.group(0))
            degree_level = level
            break

    branch_patterns = [
        r"computer science and engineering",
        r"computer science",
        r"information technology",
        r"information science",
        r"electronics and communication engineering",
        r"electrical and electronics engineering",
        r"mechanical engineering",
        r"civil engineering",
    ]

    branch = ""

    for pattern in branch_patterns:
        match = re.search(pattern, lower)

        if match:
            branch = match.group(0)
            break

    years = [
        int(year)
        for year in re.findall(r"\b(?:19|20)\d{2}\b", text)
    ]

    cgpa_match = re.search(
        r"\b(?:cgpa|gpa)\s*[:\-]?\s*(\d+(?:\.\d+)?)",
        text,
        re.I,
    )

    return {
        "degree_raw": degree_raw,
        "degree_level": degree_level,
        "branch": branch,
        "start_year": min(years) if years else None,
        "end_year": max(years) if years else None,
        "cgpa": float(cgpa_match.group(1)) if cgpa_match else None,
    }


def _extract_links(text: str) -> dict[str, str]:
    """Extract LinkedIn and GitHub URLs."""
    linkedin = re.search(
        r"https?://(?:www\.)?linkedin\.com/[^\s|]+",
        text,
        re.I,
    )

    github = re.search(
        r"https?://(?:www\.)?github\.com/[^\s|]+",
        text,
        re.I,
    )

    return {
        "linkedin": linkedin.group(0).rstrip(".,;") if linkedin else "",
        "github": github.group(0).rstrip(".,;") if github else "",
    }


def _extract_certifications(text: str) -> list[str]:
    """Extract non-empty certification lines."""
    return [
        line.strip(" -•|")
        for line in text.splitlines()
        if line.strip(" -•|")
    ]


def build_resume_profile(parsed_resume: dict[str, Any]) -> dict[str, Any]:
    """Build the normalized resume JSON used by the matcher."""
    raw_sections = parsed_resume.get("sections", {})

    if not isinstance(raw_sections, dict):
        raw_sections = {}

    sections = {
        "summary": raw_sections.get(
            "professional_summary",
            raw_sections.get("summary", ""),
        ),
        "skills": raw_sections.get("skills", ""),
        "experience": raw_sections.get("experience", ""),
        "projects": raw_sections.get("projects", ""),
        "education": raw_sections.get("education", ""),
        "certifications": raw_sections.get("certifications", ""),
    }

    personal_info = parsed_resume.get("personal_info", {})

    if not isinstance(personal_info, dict):
        personal_info = {}

    all_text = "\n".join(str(value) for value in sections.values())
    all_text += "\n" + str(raw_sections.get("other", ""))

    personal_info = {
        "name": personal_info.get("name", ""),
        "email": personal_info.get("email", ""),
        "phone": personal_info.get("phone", ""),
        "links": _extract_links(all_text),
    }

    scanned = scan_resume({"sections": sections})

    experience = _extract_experience(sections["experience"])
    education = _extract_education(sections["education"])

    certifications = _extract_certifications(
        sections["certifications"]
    )

    return {
        "personal_info": personal_info,
        "sections": sections,
        "skills": scanned["skills"],
        "all_technical_skills": scanned["all_technical_skills"],
        "all_soft_skills": scanned.get(
            "all_soft_skills",
            sorted(scanned["soft_skills"]),
        ),
        "all_skills": sorted(scanned["all_skills"]),
        "experience": experience,
        "education": education,
        "certifications": certifications,
    }
