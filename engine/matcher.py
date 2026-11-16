
"""Pure-Python skill matching with optional per-skill embedding fallback."""

from __future__ import annotations
import re
from typing import Any
from difflib import SequenceMatcher

from .normalize import canon, load_dictionary
from .schemas import MatchItem, MatchEvidence

def _cosine(a: list[float], b: list[float]) -> float:
    """Calculate cosine similarity between two embedding vectors."""

    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5

    return dot / (na * nb) if na and nb else 0.0


class SemanticMatcher:
    """Lazy FastEmbed wrapper with individual skill embedding cache."""

    def __init__(
        self,
        model_name: str = "BAAI/bge-small-en-v1.5",
        threshold: float = 0.85,
    ):
        self.model_name = model_name
        self.threshold = threshold
        self._model = None
        self._cache: dict[str, list[float]] = {}

    def _embed(self, text: str) -> list[float]:
        if text not in self._cache:
            if self._model is None:
                try:
                    from fastembed import TextEmbedding
                except ImportError as exc:
                    raise RuntimeError(
                        "Install fastembed to enable semantic matching."
                    ) from exc

                self._model = TextEmbedding(model_name=self.model_name)

            self._cache[text] = list(
                next(iter(self._model.embed([text])))
            )

        return self._cache[text]

    
    def match_with_score(
        self,
        jd_skill: str,
        resume_skills: set[str],
    ) -> tuple[str, float] | None:
        """Return the closest resume skill and similarity percentage."""

        if not resume_skills:
            return None

        target = self._embed(jd_skill)

        best_score = 0.0
        best_skill = None

        for resume_skill in sorted(resume_skills):
            score = _cosine(target, self._embed(resume_skill))

            if score > best_score:
                best_score = score
                best_skill = resume_skill

        if best_skill is not None and best_score >= self.threshold:
            return best_skill, round(best_score * 100, 2)

        return None

    def match(
        self,
        jd_skill: str,
        resume_skills: set[str],
    ) -> str | None:
        """Backward-compatible skill-only matching."""

        result = self.match_with_score(jd_skill, resume_skills)
        return result[0] if result else None


def _get_resume_skills(
    resume_scan: dict[str, Any],
) -> set[str]:
    """Get canonical technical skills from resume scan output."""

    raw_skills = resume_scan.get(
        "all_technical_skills",
        resume_scan.get(
            "technical_skills",
            resume_scan.get("all_skills", []),
        ),
    )

    return {canon(skill) for skill in raw_skills}


def _get_evidence(
    resume_scan: dict[str, Any],
    skill: str,
) -> list[str]:
    """Get resume sections supporting a matched technical skill."""

    skills_data = resume_scan.get("skills", {})

    # Current resume_scan structure:
    # skills -> technical -> python -> sources
    if "technical" in skills_data:
        skill_data = skills_data.get("technical", {}).get(skill, {})
    else:
        # Backward compatibility with an older flat structure.
        skill_data = skills_data.get(skill, {})

    return sorted(set(skill_data.get("sources", [])))


def _find_implied_match(
    jd_skill: str,
    resume_skills: set[str],
    implications: dict[str, list[str]],
) -> str | None:
    """Find a resume skill that satisfies a broader JD category."""

    implied_skills = {
        canon(skill)
        for skill in implications.get(jd_skill, [])
    }

    matches = sorted(implied_skills & resume_skills)

    return matches[0] if matches else None


def _normalize_item(item: Any) -> Any:
    """Convert Pydantic requirement objects into ordinary Python data."""

    if hasattr(item, "model_dump"):
        return item.model_dump()

    return item


def match_items(
    items: list[Any],
    resume_scan: dict[str, Any],
    semantic: SemanticMatcher | None = None,
) -> list[dict[str, Any]]:
    """
    Match JD requirements against resume technical skills.

    Matching order:
        1. Exact matching
        2. Implied category matching
        3. Optional semantic matching for individual skills

    OR groups are satisfied when at least one alternative matches.
    """

    resume_skills = _get_resume_skills(resume_scan)
    implications = load_dictionary().get("implies", {})
    output = []

    for original_item in items:
        item = _normalize_item(original_item)

        # ---------------------------------
        # OR group matching
        # ---------------------------------
        if isinstance(item, dict) and "any_of" in item:
            candidates = list(
                dict.fromkeys(canon(x) for x in item["any_of"])
            )

            found = next(
                (skill for skill in candidates if skill in resume_skills),
                None,
            )

            match_type = "any_of"

            if not found:
                for candidate in candidates:
                    found = _find_implied_match(
                        candidate,
                        resume_skills,
                        implications,
                    )

                    if found:
                        match_type = "implied"
                        break

            output.append({
                "item": {"any_of": candidates},
                "status": "matched" if found else "missing",
                "match_type": match_type,
                "matched_skill": found,
                "similarity": None,
                "evidence": (
                    _get_evidence(resume_scan, found) if found else []
                ),
            })

            continue

        # ---------------------------------
        # Individual skill matching
        # ---------------------------------
        skill = canon(str(item))

        # 1. Exact match
        if skill in resume_skills:
            output.append({
                "item": skill,
                "status": "matched",
                "match_type": "exact",
                "matched_skill": skill,
                "similarity": None,
                "evidence": _get_evidence(resume_scan, skill),
            })

            continue

        # 2. Implied category match
        implied_match = _find_implied_match(
            skill,
            resume_skills,
            implications,
        )

        if implied_match:
            output.append({
                "item": skill,
                "status": "matched",
                "match_type": "implied",
                "matched_skill": implied_match,
                "similarity": None,
                "evidence": _get_evidence(resume_scan, implied_match),
            })

            continue

        # 3. Optional semantic matching
        semantic_result = None

        if semantic is not None:
            if hasattr(semantic, "match_with_score"):
                semantic_result = semantic.match_with_score(
                    skill,
                    resume_skills,
                )
            else:
                semantic_match = semantic.match(
                    skill,
                    resume_skills,
                )

                if semantic_match:
                    semantic_result = (semantic_match, None)

        if semantic_result:
            semantic_match, similarity = semantic_result

            output.append({
                "item": skill,
                "status": "matched",
                "match_type": "semantic",
                "matched_skill": semantic_match,
                "similarity": similarity,
                "evidence": _get_evidence(
                    resume_scan,
                    semantic_match,
                ),
            })

        else:
            output.append({
                "item": skill,
                "status": "missing",
                "match_type": "exact",
                "matched_skill": None,
                "similarity": None,
                "evidence": [],
            })

    return output


def _evidence_level(sections: list[str]) -> str:
    """Determine evidence strength from resume sections."""

    if any(section in {"experience", "projects"} for section in sections):
        return "demonstrated"

    if "skills" in sections or "technical_skills" in sections:
        return "claimed"

    return "mentioned"


def _match_skill_results(
    items: list[Any],
    resume_scan: dict[str, Any],
    semantic: SemanticMatcher | None = None,
) -> list[MatchItem]:
    """Convert existing skill matches into canonical MatchItem objects."""

    raw_results = match_items(items, resume_scan, semantic)
    results = []

    for result in raw_results:
        status = result["status"]
        match_type = result.get("match_type")
        matched_skill = result.get("matched_skill")

        sections = (
            _get_evidence(resume_scan, matched_skill)
            if matched_skill
            else []
        )

        item = result["item"]
        matched_with = [matched_skill] if matched_skill else []

        # Semantic matches receive partial credit.
        if match_type == "semantic" and status == "matched":
            status = "partial"

        evidence = None

        if sections:
            evidence = MatchEvidence(
                sections=sections,
                level=_evidence_level(sections),
            )

        results.append(
            MatchItem(
                item=item,
                kind="skill",
                status=status,
                match_type=match_type,
                matched_with=matched_with,
                similarity=result.get("similarity"),
                evidence=evidence,
            )
        )

    return results


def match_experience(
    jd_experience: Any,
    resume_scan: dict[str, Any],
) -> MatchItem | None:
    """Match experience duration and, when specified, experience domain."""

    if jd_experience is None:
        return None

    def get_value(obj, key, default=None):
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    resume_experience = resume_scan.get("experience", {}) or {}

    professional = resume_experience.get("professional_months", 0) or 0
    internship = resume_experience.get("internship_months", 0) or 0

    candidate_months = professional + (0.5 * internship)

    minimum = get_value(jd_experience, "min_months", 0) or 0
    maximum = get_value(jd_experience, "max_months")
    domain = get_value(jd_experience, "domain")

    # Check domain only against work-experience text and job titles.
    section_text = resume_scan.get("section_text", {}) or {}
    experience_text = section_text.get("experience", "")

    records = resume_experience.get("records", []) or []
    record_titles = " ".join(
        str(record.get("title", ""))
        for record in records
        if isinstance(record, dict)
    )

    searchable_text = f"{experience_text} {record_titles}".lower()

    ignored_domain_words = {
        "experience", "experienced", "professional",
        "development", "developing", "developer",
        "building", "built", "working", "worked",
        "years", "year", "months", "month",
        "with", "within", "from", "into", "for",
        "and", "the", "of", "in", "on", "a", "an","driven"
    }

    def normalize_tokens(value: str) -> set[str]:
        tokens = re.findall(r"[a-z0-9]+", value.lower())

        return {
            token[:-1] if token.endswith("s") and len(token) > 4 else token
            for token in tokens
            if token not in ignored_domain_words
        }

    domain_tokens = normalize_tokens(domain) if domain else set()
    resume_tokens = normalize_tokens(searchable_text)

    matched_domain_tokens = domain_tokens & resume_tokens

    domain_matched = (
        not domain_tokens
        or domain_tokens.issubset(resume_tokens)
    )

    months_matched = candidate_months >= minimum

    status = (
        "matched"
        if months_matched and domain_matched
        else "missing"
    )

    shortfall = max(0, minimum - candidate_months)

    return MatchItem(
        item={
            "min_months": minimum,
            "max_months": maximum,
            "domain": domain,
        },
        kind="experience",
        status=status,
        detail={
            "professional_months": professional,
            "internship_months": internship,
            "internship_weight": 0.5,
            "candidate_months": candidate_months,
            "required_min_months": minimum,
            "required_max_months": maximum,
            "shortfall_months": shortfall,
            "domain_required": bool(domain_tokens),
            "domain_matched": domain_matched,
            "domain_tokens": sorted(domain_tokens),
            "matched_domain_tokens": sorted(matched_domain_tokens),
        },
    )


def match_education(
    jd_education: Any,
    resume_scan: dict[str, Any],
) -> MatchItem | None:

    if jd_education is None:
        return None

    def get_value(obj, key, default=None):
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    resume_education = resume_scan.get("education", {}) or {}

    jd_level = str(get_value(jd_education, "level", "none")).lower()
    jd_branches = [
        str(branch).lower()
        for branch in get_value(jd_education, "branches", [])
    ]
    alternatives = [
        str(value).lower()
        for value in get_value(jd_education, "alternatives", [])
    ]

    resume_level = str(
        get_value(
            resume_education,
            "degree_level",
            get_value(resume_education, "level", "none"),
        )
    ).lower()

    resume_branch = str(
        get_value(resume_education, "branch", "")
    ).lower()

    level_order = {
        "none": 0,
        "high school": 1,
        "diploma": 2,
        "associate": 3,
        "bachelor": 4,
        "master": 5,
        "doctorate": 6,
    }

    level_ok = (
        jd_level == "none"
        or (
            resume_level in level_order
            and jd_level in level_order
            and level_order[resume_level] >= level_order[jd_level]
        )
    )

    branch_aliases = {
        "cs": "computer science",
        "cse": "computer science",
        "it": "information technology",
        "ece": "electronics engineering",
        "eee": "electrical engineering",
        "me": "mechanical engineering",
        "ce": "civil engineering",
    }

    normalized_jd_branches = [
        branch_aliases.get(branch, branch)
        for branch in jd_branches
    ]

    normalized_resume_branch = branch_aliases.get(
        resume_branch,
        resume_branch,
    )

    branch_ok = (
        not normalized_jd_branches
        or any(
            branch in normalized_resume_branch
            or normalized_resume_branch in branch
            for branch in normalized_jd_branches
            if normalized_resume_branch
        )
    )

    alternative_present = "equivalent experience" in alternatives

    if level_ok and branch_ok:
        status = "matched"
        reason = "degree_and_branch_match"
    elif alternative_present:
        # Alternative evidence will be checked separately.
        status = "missing"
        reason = "alternative_requires_verification"
    else:
        status = "missing"
        reason = "education_requirement_not_met"

    return MatchItem(
        item={
            "level": jd_level,
            "branches": jd_branches,
            "alternatives": alternatives,
        },
        kind="education",
        status=status,
        detail={
            "resume_level": resume_level,
            "resume_branch": resume_branch,
            "level_match": level_ok,
            "branch_match": branch_ok,
            "alternative_present": alternative_present,
            "reason": reason,
        },
    )


def match_certifications(
    jd_certifications: list[str],
    resume_scan: dict[str, Any],
) -> list[MatchItem]:

    import re

    def normalize(value: str) -> str:
        value = str(value).lower()

        # Remove classification wording from JD requirements.
        value = re.sub(
            r"\b(?:is\s+)?(?:preferred|required|mandatory|"
            r"nice\s+to\s+have|good\s+to\s+have|must\s+have)\b",
            "",
            value,
        )

        # Ignore the word "certified" but preserve certification levels.
        value = re.sub(r"\bcertified\b", "", value)

        # Remove special characters and control characters.
        value = re.sub(r"[^a-z0-9]+", " ", value)

        return " ".join(value.split())

    FUZZY_THRESHOLD = 85.0

    resume_certifications = resume_scan.get("certifications", []) or []

    if isinstance(resume_certifications, str):
        resume_certifications = [resume_certifications]

    results = []

    for jd_cert in jd_certifications or []:
        jd_normalized = normalize(jd_cert)
        jd_tokens = set(jd_normalized.split())

        closest_cert = None
        best_similarity = 0.0
        best_match_type = "none"

        for resume_cert in resume_certifications:
            resume_normalized = normalize(resume_cert)

            if not resume_normalized:
                continue

            resume_tokens = set(resume_normalized.split())

            # Allow issuer names, dates, and additional qualification
            # details in the resume certification entry.
            if jd_tokens and jd_tokens.issubset(resume_tokens):
                similarity = 100.0
            else:
                similarity = round(
                    SequenceMatcher(
                        None,
                        jd_normalized,
                        resume_normalized,
                    ).ratio() * 100,
                    2,
                )

            if similarity > best_similarity:
                best_similarity = similarity
                closest_cert = resume_cert
                best_match_type = (
                    "exact"
                    if jd_normalized == resume_normalized
                    else "fuzzy"
                )

        is_matched = best_similarity >= FUZZY_THRESHOLD

        results.append(
            MatchItem(
                item=jd_cert,
                kind="certification",
                status="matched" if is_matched else "missing",
                similarity=best_similarity,
                matched_with=[closest_cert] if is_matched else [],
                detail={
                    "closest_resume_cert": closest_cert,
                    "similarity": best_similarity,
                    "fuzzy_threshold": FUZZY_THRESHOLD,
                    "match_type": best_match_type if is_matched else "none",
                },
            )
        )

    return results
