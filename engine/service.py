
"""Orchestration layer for deterministic resume and JD analysis."""

from __future__ import annotations

import re
from typing import Any
from pathlib import Path
from .normalize import canon, skill_patterns
from .llm_fallback import extract_unresolved, literal_match
from .jd_parser import parse_jd
from .resume_scan import scan_resume
from .matcher import (
    SemanticMatcher,
    _match_skill_results,
    match_experience,
    match_education,
    match_certifications,
)
from .scorer import calculate_score
from .report import build_report
from .suggestions import generate_suggestions

def _flatten(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        return " ".join(_flatten(v) for v in value.values())
    if isinstance(value, (list, tuple, set)):
        return " ".join(_flatten(v) for v in value)
    return str(value)



def _extract_resume_education(resume_json: dict) -> dict:
    """Extract degree level and branches from resume education."""

    sections = resume_json.get("sections", {})
    text = _flatten(sections.get("education", {})).lower()

    degree_patterns = [
        ("doctorate", r"\b(ph\.?d|doctorate)\b"),
        ("master", r"\b(m\.tech|m\.e|m\.sc|mca|master)\b"),
        ("bachelor", r"\b(b\.tech|b\.e|b\.sc|bca|bachelor)\b"),
        ("diploma", r"\bdiploma\b"),
        ("associate", r"\bassociate\b"),
    ]

    level = "none"

    for degree, pattern in degree_patterns:
        if re.search(pattern, text):
            level = degree
            break

    branch_patterns = {
    "computer science": r"\b(computer science|cse|cs)\b",
    "information technology": r"\b(information technology|information science|it)\b",
    "mechanical engineering": r"\b(mechanical engineering|mechanical|me)\b",
    "electrical engineering": r"\b(electrical engineering|electrical|eee)\b",
    "electronics engineering": r"\b(electronics and communication engineering|electronics engineering|electronics|ece)\b",
    "civil engineering": r"\b(civil engineering|civil|ce)\b",
    "chemical engineering": r"\b(chemical engineering|chemical)\b",
    "biotechnology": r"\b(biotechnology|biotech)\b",
}

    branches = [
        branch
        for branch, pattern in branch_patterns.items()
        if re.search(pattern, text)
    ]

    return {
        "level": level,
        "branches": branches,
        "branch": " ".join(branches),
    }




def _get_requirement_items(group: Any) -> tuple[list, list, Any, Any, list]:
    """Read scored requirements while excluding non-technical languages."""

    if hasattr(group, "model_dump"):
        group = group.model_dump()

    group = group or {}

    return (
        group.get("skills", []) or [],
        group.get("experience"),
        group.get("education"),
        group.get("certifications", []) or [],
        group.get("other", []) or [],
    )


def _build_side_results(group, resume, semantic):
    """Create MatchItems for all scored requirements in one JD side."""

    skills, experience, education, certifications, _other = (
        _get_requirement_items(group)
    )

    results = _match_skill_results(skills, resume, semantic)

    experience_result = match_experience(experience, resume)
    if experience_result is not None:
        results.append(experience_result)

    education_result = match_education(education, resume)
    if education_result is not None:
        results.append(education_result)

    results.extend(match_certifications(certifications, resume))

    return results
def _extract_resume_experience(resume: dict) -> dict:
    """Extract experience totals from normalized or raw resume data."""

    experience = resume.get("experience", {}) or {}

    professional = experience.get("professional_months", 0) or 0
    internship = experience.get("internship_months", 0) or 0

    if professional or internship:
        return {
            "professional_months": professional,
            "internship_months": internship,
        }

    from .profile_builder import _extract_experience

    sections = resume.get("section_text", {})
    experience_text = sections.get("experience", "")

    if not experience_text:
        raw_sections = resume.get("sections", {})
        experience_text = (
            raw_sections.get("work_experience")
            or raw_sections.get("professional_experience")
            or raw_sections.get("experience")
            or raw_sections.get("internships")
            or ""
        )

    return _extract_experience(_flatten(experience_text))

def analyze(
    resume_json: dict[str, Any],
    jd_text: str,
    *,
    use_llm_fallback: bool = False,
    use_semantic: bool = True,
    semantic_matcher: SemanticMatcher | None = None,
) -> dict:
    """Analyze a resume against a job description."""

    jd = parse_jd(jd_text)
    print("REQUIRED:", jd.required.model_dump())
    print("PREFERRED:", jd.preferred.model_dump())
    print("CONDITIONS:", jd.job_conditions.model_dump())
    resume = scan_resume(resume_json)

    llm_added: list[str] = []
    llm_used = False
    llm_warnings: list[str] = []

    if use_llm_fallback and jd.unresolved_skill_bullets:
        known_terms = {
            term
            for patterns in skill_patterns().values()
            for alias, _ in patterns
            for term in (alias.lower(), canon(alias))
        }

        llm_result = extract_unresolved(
            jd.unresolved_skill_bullets,
            known_terms,
            canon=canon,
            cache_path=Path("data/llm_cache.json"),
            log_path=Path("data/unresolved_skills.jsonl"),
            jd_title=jd.title,
        )

        llm_added = llm_result.terms
        llm_warnings = llm_result.warnings
        llm_used = bool(
            llm_result.calls
            or llm_result.cache_hits
            or llm_result.warnings
        )

    semantic = semantic_matcher

    if semantic is None and use_semantic:
        semantic = SemanticMatcher()

    # Normalize education and experience.
    resume["education"] = _extract_resume_education(resume_json)
    resume["experience"] = _extract_resume_experience(resume)
    # Check LLM-extracted skills against actual resume text.
    llm_matches = []

    for skill in llm_added:
        matched_sections = literal_match(skill, resume.get("sections", {}))

        llm_matches.append({
        "skill": skill,
        "status": "matched" if matched_sections else "missing",
        "match_type": "literal",
        "source": "llm",
        "evidence_sections": matched_sections,
    })

    required_results = _build_side_results(
        jd.required,
        resume,
        semantic,
    )

    preferred_results = _build_side_results(
        jd.preferred,
        resume,
        semantic,
    )

    # Score every result exactly once.
    breakdown = calculate_score(
        required_results,
        preferred_results,
        jd,
        resume,
    )

    report = build_report(
        required_results=required_results,
        preferred_results=preferred_results,
        breakdown=breakdown,
        jd_soft=jd.soft_skills,
        resume_soft=resume.get("all_soft_skills", []),
        llm_added=llm_added,
        llm_matches=llm_matches,
        llm_used=llm_used,
        job_conditions=jd.job_conditions,
        other_requirements=(
            jd.required.other + jd.preferred.other
        ),
    )

    report["warnings"].extend(llm_warnings)
    missing_required = [
        item["item"]
        for item in report["required"]["missing"]
        if item["kind"] == "skill"
        and isinstance(item["item"], str)
    ]

    missing_preferred = [
        item["item"]
        for item in report["preferred"]["missing"]
        if item["kind"] == "skill"
        and isinstance(item["item"], str)
    ]

    report["suggestions"] = generate_suggestions(
        missing_required,
        missing_preferred,
    )
    return report