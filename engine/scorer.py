
"""Deterministic scoring for resume and job-description matching."""

from typing import Any


REQUIRED_WEIGHT = 0.70
PREFERRED_WEIGHT = 0.30


def _get(item: Any, key: str, default=None):
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def _model_data(value: Any) -> dict:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return value or {}


def _side_score(results: list) -> dict:
    matched = [x for x in results if _get(x, "status") == "matched"]
    partial = [x for x in results if _get(x, "status") == "partial"]
    missing = [x for x in results if _get(x, "status") == "missing"]

    total = len(results)

    if len(matched) + len(partial) + len(missing) != total:
        raise RuntimeError("Scoring invariant violated.")

    credit = len(matched) + 0.5 * len(partial)
    percentage = credit / total * 100 if total else 0.0

    return {
        "matched": len(matched),
        "partial": len(partial),
        "missing": len(missing),
        "total": total,
        "credit": round(credit, 2),
        "percentage": round(percentage, 2),
        "matched_items": matched,
        "partial_items": partial,
        "missing_items": missing,
    }


def _education_score(required_education, resume_education):
    required = _model_data(required_education)
    resume = _model_data(resume_education)

    required_level = required.get("level", "none")
    candidate_level = resume.get(
    "degree_level",
    resume.get("level", "none"),
)

    levels = {
        "none": 0,
        "high_school": 1,
        "diploma": 2,
        "associate": 3,
        "bachelor": 4,
        "master": 5,
        "doctorate": 6,
    }

    level_ok = (
        levels.get(required_level, 0) == 0
        or levels.get(candidate_level, 0) >= levels.get(required_level, 0)
    )

    required_branches = {
        str(x).lower() for x in required.get("branches", [])
    }
    candidate_branch = resume.get("branch", "")
    candidate_branches = (
        {str(candidate_branch).lower()}
        if candidate_branch
        else {
              str(x).lower()
              for x in resume.get("branches", [])
    }
)

    branch_ok = (
        not required_branches
        or bool(required_branches & candidate_branches)
    )

    return {
        "ok": level_ok and branch_ok,
        "level_ok": level_ok,
        "branch_ok": branch_ok,
        "required_level": required_level,
        "candidate_level": candidate_level,
        "required_branches": sorted(required_branches),
        "candidate_branches": sorted(candidate_branches),
        "score": 1.0 if level_ok and branch_ok else 0.0,
    }


def _experience_score(required_experience, resume_experience):
    required = _model_data(required_experience)
    resume = _model_data(resume_experience)

    professional = resume.get("professional_months", 0) or 0
    internship = resume.get("internship_months", 0) or 0

    candidate_months = professional + 0.5 * internship
    minimum = required.get("min_months", required.get("min", 0)) or 0
    maximum = required.get("max_months", required.get("max"))

    return {
        "ok": candidate_months >= minimum,
        "candidate_months": round(candidate_months, 2),
        "professional_months": professional,
        "internship_months": internship,
        "required_min_months": minimum,
        "required_max_months": maximum,
        "shortfall_months": round(max(0, minimum - candidate_months), 2),
        "score": 1.0 if candidate_months >= minimum else 0.0,
    }


def calculate_score(
    required_results: list,
    preferred_results: list,
    jd: Any,
    resume: dict,
) -> dict:
    """Score every required and preferred MatchItem exactly once."""

    jd = _model_data(jd)
    required_group = _model_data(jd.get("required", {}))
    preferred_group = _model_data(jd.get("preferred", {}))

    required = _side_score(required_results)
    preferred = _side_score(preferred_results)

    if required["total"] == 0 and preferred["total"] == 0:
        required_weight = 0.0
        preferred_weight = 0.0
        final_score = 0.0
    elif preferred["total"] == 0:
        required_weight = 1.0
        preferred_weight = 0.0
        final_score = required["percentage"]
    elif required["total"] == 0:
        required_weight = 0.0
        preferred_weight = 1.0
        final_score = preferred["percentage"]
    else:
        required_weight = REQUIRED_WEIGHT
        preferred_weight = PREFERRED_WEIGHT
        final_score = (
            required["percentage"] * required_weight
            + preferred["percentage"] * preferred_weight
        )

    education = _education_score(
        required_group.get("education", {}),
        resume.get("education", {}),
    )

    experience = _experience_score(
        required_group.get("experience", required_group.get("experience_months", {})),
        resume.get("experience", {}),
    )

    def side_output(data, weight):
        return {
            "matched": data["matched"],
            "partial": data["partial"],
            "missing": data["missing"],
            "total": data["total"],
            "credit": data["credit"],
            "percentage": data["percentage"],
            "weight": round(weight * 100, 2),
        }

    return {
        "score": round(final_score),
        "breakdown": {
            "required": side_output(required, required_weight),
            "preferred": side_output(preferred, preferred_weight),
            "education": education,
            "experience": experience,
        },
        "required_matched": required["matched_items"],
        "required_partial": required["partial_items"],
        "required_missing": required["missing_items"],
        "preferred_matched": preferred["matched_items"],
        "preferred_partial": preferred["partial_items"],
        "preferred_missing": preferred["missing_items"],
    }
