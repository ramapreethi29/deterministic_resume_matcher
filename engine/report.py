
"""Final report assembly and matching invariants."""

from .normalize import load_dictionary


def _get(item, key, default=None):
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def _partition(results):
    """Partition results into matched, partial, and missing."""

    matched = [
        item for item in results
        if _get(item, "status") == "matched"
    ]

    partial = [
        item for item in results
        if _get(item, "status") == "partial"
    ]

    missing = [
        item for item in results
        if _get(item, "status") == "missing"
    ]

    if len(matched) + len(partial) + len(missing) != len(results):
        raise RuntimeError("Matching invariant violated.")

    return matched, partial, missing


def _partition_all(results):
    return _partition(results)


def _format_item(item):
    """Format a MatchItem without discarding useful details."""

    result = {
        "item": _get(item, "item"),
        "kind": _get(item, "kind", "skill"),
        "status": _get(item, "status"),
    }

    for field in (
        "match_type",
        "matched_with",
        "similarity",
        "evidence",
        "detail",
    ):
        value = _get(item, field)

        if value is not None and value != []:
            if hasattr(value, "model_dump"):
                value = value.model_dump()
            result[field] = value

    return result


def _format_skill_name(skill):
    """Convert canonical skill names to configured display names."""

    skills = load_dictionary().get("skills", {})
    details = skills.get(skill, {})

    return details.get("display_name", skill)


def _missing_gaps(results):
    """Collect missing skills only. Other requirement types are excluded."""

    gaps = []

    for item in results:
        if _get(item, "status") != "missing":
            continue

        if _get(item, "kind") != "skill":
            continue

        value = _get(item, "item")

        if isinstance(value, dict) and "any_of" in value:
            gaps.extend(value["any_of"])
        else:
            gaps.append(value)

    return sorted({
        (
            "object oriented programming"
            if str(skill) == "oop"
            else _format_skill_name(str(skill))
        )
        for skill in gaps
    })


def _side_result(results):
    matched, partial, missing = _partition_all(results)

    return {
        "total": len(results),
        "matched": [_format_item(x) for x in matched],
        "partial": [_format_item(x) for x in partial],
        "missing": [_format_item(x) for x in missing],
    }


def _format_other_requirement(item):
    """Keep non-scored requirements visible as unverified."""

    if isinstance(item, str):
        return {
            "item": item,
            "status": "unverified",
        }

    value = _get(item, "item", item)
    status = _get(item, "status", "unverified")

    return {
        "item": value,
        "status": status,
    }


def _format_job_conditions(conditions):
    """Preserve job-condition fields supplied by the JD parser."""

    fields = (
        "location",
        "work_mode",
        "employment_type",
        "notice_period",
        "shift",
    )

    return {
        field: _get(conditions, field)
        for field in fields
    }

def build_report(
    required_results,
    preferred_results,
    breakdown,
    education_detail=None,
    candidate_months=0,
    required_min=0,
    jd_soft=None,
    resume_soft=None,
    llm_added=None,
    llm_matches=None,
    llm_used=False,
    job_conditions=None,
    other_requirements=None,
):
    """Build the canonical resume matching report."""

    required = _side_result(required_results)
    preferred = _side_result(preferred_results)

    score_details = breakdown["breakdown"]
    score_breakdown = {}

    for category, results in (
        ("required", required_results),
        ("preferred", preferred_results),
    ):
        matched, partial, missing = _partition_all(results)

        total = len(results)
        credit = len(matched) + 0.5 * len(partial)
        pct = credit / total if total else 0.0

        weight = score_details[category].get("weight", 0) / 100

        score_breakdown[category] = {
            "weight": weight,
            "credit": round(credit, 2),
            "total": total,
            "pct": round(pct, 4),
            "points": round(weight * pct * 100, 2),
        }

    return {
        "score": breakdown["score"],
        "score_breakdown": score_breakdown,
        "required": required,
        "preferred": preferred,
        "llm_skill_matches": llm_matches or [],
        "soft_skills": {
            "jd": sorted(set(jd_soft or [])),
            "resume": sorted(set(resume_soft or [])),
            "scored": False,
        },
        "other_requirements": [
            _format_other_requirement(item)
            for item in (other_requirements or [])
        ],
        "job_conditions": _format_job_conditions(job_conditions),
        "gaps": sorted(set(
            _missing_gaps(required_results)
            + _missing_gaps(preferred_results)
        )),
        "warnings": [],
        "suggestions": [],
        "meta": {
            "engine_version": "0.1.0",
            "skills_dictionary_version": 2,
            "llm_used": llm_used,
            "semantic_matches": sum(
                1
                for item in required_results + preferred_results
                if _get(item, "match_type") == "semantic"
            ),
            "invariants_ok": True,
            "processing_ms": 0,
        },
    }