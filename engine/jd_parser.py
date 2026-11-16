
"""Deterministic job-description parsing.

Only required.skills and preferred.skills are scored.
Responsibilities and soft skills are stored for display only.
Matching and scoring remain Python-only.
"""

from __future__ import annotations

import re
from typing import Any

from .normalize import canon, skill_patterns, skill_type
from .schemas import JDResult


HEADINGS = {
    "required": {
        "required",
        "required skills",
        "requirements",
        "must have",
        "minimum qualifications",
        "required qualifications",
        "technical requirements",
    },
    "preferred": {
        "preferred",
        "preferred skills",
        "nice to have",
        "good to have",
        "bonus",
        "preferred qualifications",
    },
    "preferred_certifications": {
    "preferred certifications",
    "nice-to-have certifications",
},
    "responsibilities": {
        "key responsibilities",
        "responsibilities",
        "roles and responsibilities",
        "what you will do",
        "what you'll do",
        "duties",
    },
    "soft_skills": {
        "soft skills",
        "personal skills",
        "interpersonal skills",
    },
    "education": {
    "education",
    "educational qualifications",
    "academic qualifications",
    "qualifications",
    "academic background",
    "educational background",
},
    "experience": {
    "experience",
    "work experience",
    "professional experience",
},
    "certifications": {
        "certifications",
        "required certifications",
        "professional certifications",
    },
    "languages": {
        "languages",
        "language requirements",
        "spoken languages",
    },
    "other": {
        "other requirements",
        "additional requirements",
        "additional qualifications",
    },
    "job_conditions": {
    "job details",
    "job conditions",
    "work conditions",
    "employment details",
    "location",
    "work location",
    "job location",
    "work mode",
    "work arrangement",
    "employment type",
    "job type",
    "notice period",
    "shift",
    "working hours",
},
"company_info": {
    "about us",
    "about the company",
    "company overview",
    "about the role",
    "role overview",
    "job summary",
    "benefits",
    "what we offer",
    "perks and benefits",
},
}
SECTION_NAMES = [
    "header",
    "required",
    "preferred",
    "responsibilities",
    "soft_skills",
    "education",
    "experience",
    "certifications",
    "preferred_certifications",
    "languages",
    "other",
    "job_conditions",
    "company_info",
]

BULLETS = ("•", "*", "-", "–", "▪", "‣")


PREFERRED_CUES = re.compile(
    r"\b(preferred|desirable|a plus|nice to have|"
    r"good to have|bonus|ideally|advantage|added advantage)\b",
    re.I,
)

REQUIRED_CUES = re.compile(
    r"\b(must|required|mandatory|minimum requirement|"
    r"must have|essential)\b",
    re.I,
)

RESPONSIBILITY_CUES = re.compile(
    r"^(responsibilities include|key responsibilities|"
    r"you will\b|you'll\b|responsible for\b|"
    r"your role\b|duties include|what you will do)",
    re.I,
)

EDUCATION_CUES = re.compile(
    r"\b(bachelor|b\.?\s*tech|b\.?\s*e\.?|b\.?\s*sc|"
    r"master|m\.?\s*tech|m\.?\s*e\.?|m\.?\s*sc|"
    r"ph\.?\s*d|doctorate|degree|graduation|"
    r"computer science|information technology|"
    r"equivalent experience|equivalent practical experience|"
    r"equivalent work experience)\b",
    re.I,
)
def _has_experience_requirement(text: str) -> bool:
    """Identify actual experience requirements, including domain-only statements."""

    text = text.strip()

    # Fresher or entry-level requirements
    if re.search(
        r"\b(freshers?|entry[- ]level|no experience required)\b",
        text,
        re.I,
    ):
        return True

    # Numeric experience requirements
        # Numeric experience requirements, including "3+ years"
    if re.search(
        r"\b(?:"
        r"\d+\s*\+\s*(?:years?|months?)"
        r"|\d+\s*(?:years?|months?)"
        r"|at least\s+\d+"
        r"|minimum\s+of\s+\d+"
        r"|up to\s+\d+"
        r")\b",
        text,
        re.I,
    ):
        return True

    # Domain-only experience statements
    if re.search(
        r"\bexperience\s+(?:in|building|developing|"
        r"working\s+on|working\s+with|managing|"
        r"leading|designing|implementing)\b",
        text,
        re.I,
    ):
        return True

    return False
EXPERIENCE_CUES = re.compile(
    r"\b(years?|months?)\b",
    re.I,
)

CERTIFICATION_CUES = re.compile(
    r"\b(certification|certifications|certified|certificate)\b",
    re.I,
)

BRANCHES = [
    "computer science and engineering",
    "computer science",
    "information technology",
    "information science",
    "software engineering",
    "electronics and communication",
    "electrical engineering",
    "mechanical engineering",
    "engineering",
]


# -------------------------------------------------------------------
# 1. JD section splitting
# -------------------------------------------------------------------

def split_jd(text: str) -> dict[str, list[str]]:
    """Split JD text using headings, including inline Markdown headings."""

    sections = {name: [] for name in SECTION_NAMES}
    current = "header"

    heading_names = sorted(
        {
            heading
            for headings in HEADINGS.values()
            for heading in headings
        },
        key=len,
        reverse=True,
    )

    pattern = re.compile(
    r"(?i)(?<!\w)\*{0,2}\s*("
    + "|".join(re.escape(h) for h in heading_names)
    + r")\s*:\*{0,2}"
)

    text = pattern.sub(
    lambda match: "\n" + match.group(1) + ":\n",
    text or "",
)

    for raw in text.splitlines():
        line = raw.strip()

        if not line:
            continue

        # Remove Markdown markers before checking the heading.
        line = line.strip("*#_ ").strip()

        normalized = line.lower().rstrip(":").strip()

        matched = next(
            (
                name
                for name, headings in HEADINGS.items()
                if normalized in headings
            ),
            None,
        )

        if matched:
            current = matched

            if matched == "job_conditions":
                sections[current].append(
                    f"__HEADING__:{normalized}"
                )

            continue

        cleaned = line

        while cleaned and cleaned[0] in BULLETS:
            cleaned = cleaned[1:].strip()

        if cleaned:
            sections[current].append(cleaned)

    return sections

# -------------------------------------------------------------------
# 2. Title extraction
# -------------------------------------------------------------------

def _extract_title(header_lines: list[str]) -> str:
    """Extract a standalone job title from the JD header."""

    for line in header_lines:
        cleaned = line.strip()
        cleaned = cleaned.strip("*#_ ").strip()

        cleaned = re.sub(
            r"^(job\s*title|position|role)\s*:\s*",
            "",
            cleaned,
            flags=re.I,
        ).strip()

        if not cleaned:
            continue

        # A descriptive sentence is not a standalone job title.
        if re.search(
            r"\b(we are|we're|we need|looking for|seeking|"
            r"hiring|responsible for|join our|the ideal candidate)\b",
            cleaned,
            re.I,
        ):
            continue

        # Reject sentences and long descriptions.
        if len(cleaned.split()) > 10:
            continue

        if re.search(r"[.!?]", cleaned):
            continue

        return cleaned

    return ""


# -------------------------------------------------------------------
# 3. Sentence splitting
# -------------------------------------------------------------------

def _split_sentences(text: str) -> list[str]:
    """Split sentences while preserving common technical abbreviations."""

    protected = re.sub(
        r"\b(B\.Tech|B\.E|B\.Sc|M\.Tech|M\.E|M\.Sc|Ph\.D)\.",
        lambda match: match.group(0).replace(".", "<DOT>"),
        text,
        flags=re.I,
    )

    sentences = re.split(r"(?<=[.!?])\s+", protected)

    return [
        sentence.replace("<DOT>", ".").strip()
        for sentence in sentences
        if sentence.strip()
    ]


# -------------------------------------------------------------------
# 4. Requirement classification
# -------------------------------------------------------------------

def _cue_section(line: str, default: str) -> str:
    """Classify a requirement using explicit wording."""

    if PREFERRED_CUES.search(line):
        return "preferred"

    if REQUIRED_CUES.search(line):
        return "required"

    if default == "header":
        return "required"

    return default


def _is_responsibility(line: str) -> bool:
    """Identify responsibility statements that should not be scored."""

    return bool(RESPONSIBILITY_CUES.search(line.strip()))


# -------------------------------------------------------------------
# 5. Skill extraction with exact alias boundaries
# -------------------------------------------------------------------

def _ordered_skill_mentions(text: str) -> list[tuple[str, int, int]]:
    """Find skill mentions in textual order."""

    candidates = []

    for canonical, aliases in skill_patterns().items():
        for alias, pattern in aliases:
            for match in pattern.finditer(text):
                candidates.append(
                    (
                        canonical,
                        match.start(),
                        match.end(),
                    )
                )

    # Prefer the longest alias when matches overlap.
    candidates.sort(
        key=lambda item: (
            item[1],
            -(item[2] - item[1]),
            item[0],
        )
    )

    selected = []
    last_end = -1

    for canonical, start, end in candidates:
        if start < last_end:
            continue

        selected.append((canonical, start, end))
        last_end = end

    return selected


def _is_or_connector(gap: str) -> bool:
    """Return True only when two skill mentions are joined by OR or /."""

    return bool(
        re.fullmatch(
            r"\s*(?:,?\s*or\s*|/)\s*",
            gap,
            re.I,
        )
    )


def extract_items(
    bullet: str,
) -> tuple[list[str | dict[str, list[str]]], bool]:
    """
    Extract individual skills and OR groups.

    Examples:
        Python, SQL and Docker
            -> python, sql, docker

        FastAPI or Flask
            -> any_of: [fastapi, flask]

        FastAPI or Flask, React or Angular
            -> two separate OR groups
    """

    mentions = _ordered_skill_mentions(bullet)

    if not mentions:
        return [], False

    items: list[str | dict[str, list[str]]] = []
    index = 0

    while index < len(mentions):
        current_skill, _, current_end = mentions[index]

        group = [current_skill]
        next_index = index + 1

        while next_index < len(mentions):
            next_skill, next_start, next_end = mentions[next_index]

            gap = bullet[current_end:next_start]

            if not _is_or_connector(gap):
                break

            if next_skill not in group:
                group.append(next_skill)

            current_end = next_end
            next_index += 1

        if len(group) > 1:
            items.append({"any_of": group})
            index = next_index
        else:
            if current_skill not in items:
                items.append(current_skill)

            index += 1

    return items, True


# -------------------------------------------------------------------
# 6. Experience extraction
# -------------------------------------------------------------------

def _experience(lines: list[str]) -> dict[str, Any] | None:
    """Convert JD experience requirements into months and domain."""

    if not lines:
        return None

    text = " ".join(lines).lower()

    domain = _experience_domain(text)

    # Freshers or roles requiring no prior experience.
    if re.search(
        r"\b(freshers?|entry[- ]level|no experience required)\b",
        text,
    ):
        return {
            "min_months": 0,
            "max_months": None,
            "domain": domain,
        }

    # Up to 2 years = 0–24 months.
    up_to = re.search(
        r"\bup to\s+(\d+)\s*(years?|months?)\b",
        text,
    )

    if up_to:
        amount = int(up_to.group(1))
        unit = up_to.group(2)

        maximum = amount * 12 if unit.startswith("year") else amount

        return {
            "min_months": 0,
            "max_months": maximum,
            "domain": domain,
        }

    # Supports:
    # 0-2 years
    # 1-3 years
    # 1 year to 3 years
    # 6-12 months
    range_match = re.search(
        r"\b(\d+)\s*(?:(years?|months?)\s*)?"
        r"(?:-|–|—|to)\s*(\d+)\s*(years?|months?)\b",
        text,
    )

    if range_match:
        first = int(range_match.group(1))
        first_unit = range_match.group(2) or range_match.group(4)
        second = int(range_match.group(3))
        second_unit = range_match.group(4)

        minimum = first * 12 if first_unit.startswith("year") else first
        maximum = second * 12 if second_unit.startswith("year") else second

        return {
            "min_months": minimum,
            "max_months": maximum,
            "domain": domain,
        }

    # Supports:
    # 2 years
    # 3+ years
    # 6 months
    # At least 2 years
    single = re.search(
        r"\b(\d+)\s*(?:\+)?\s*(years?|months?)\b",
        text,
    )

    if single:
        amount = int(single.group(1))
        unit = single.group(2)

        months = amount * 12 if unit.startswith("year") else amount

        return {
            "min_months": months,
            "max_months": None,
            "domain": domain,
        }

    # Domain-only experience:
    # "Experience building data-driven applications is preferred."
    if re.search(r"\bexperience\b", text):
        return {
            "min_months": 0,
            "max_months": None,
            "domain": domain,
        }

    return None


def _experience_domain(text: str) -> str | None:
    """Extract experience domains without crossing sentence boundaries."""

    patterns = [
        r"\bexperience\s+in\s+([^.;!?]+)",
        r"\bexperience\s+(?:building|developing|working\s+with|using|with)\s+([^.;!?]+)",
        r"\bbackground\s+in\s+([^.;!?]+)",
        r"\b(?:years?|months?)\s+of\s+(.+?)\s+experience\b",
    ]

    domains = []

    # Process sentences separately to avoid capturing the next sentence.
    sentences = re.split(r"[.!?;\n]+", text)

    for sentence in sentences:
        sentence = sentence.strip()

        for pattern in patterns:
            match = re.search(pattern, sentence, re.I)

            if not match:
                continue

            domain = match.group(1).strip(" .,:;-")
            domain = re.sub(
    r"\s+(?:is|are)\s+(?:preferred|required|desirable|an advantage).*$",
    "",
    domain,
    flags=re.I,
)
            # Remove introductory qualifiers.
            domain = re.sub(
                r"^(?:at least|minimum of|minimum|"
                r"more than|over|around|approximately)\s+",
                "",
                domain,
                flags=re.I,
            )

            domain = re.sub(r"\s+", " ", domain).strip()

            if domain and domain.casefold() not in {
                existing.casefold() for existing in domains
            }:
                domains.append(domain)

            break

    return "; ".join(domains) if domains else None


def _education(lines: list[str]) -> dict[str, Any] | None:
    """Extract degree level, branches and equivalent-experience alternatives."""

    if not lines:
        return None

    text = " ".join(lines).lower()
    text = re.sub(r"\s+", " ", text)

    # Degree level detection
    degree_patterns = [
        ("doctorate", r"\b(ph\.?\s*d\.?|doctorate|doctoral degree)\b"),
        (
            "master",
            r"(?<![a-z])(?:m\.?\s*tech|m\.?\s*e\.|m\.?\s*sc\.?|master'?s?|master)(?![a-z])",
        ),
        (
            "bachelor",
            r"\b(b\.?\s*tech|b\.?\s*e\.?|b\.?\s*sc|bca|bachelor'?s?|bachelor)\b",
        ),
        ("diploma", r"\bdiploma\b"),
        ("associate", r"\bassociate'?s?\b"),
    ]

    level = "none"

    for candidate, pattern in degree_patterns:
        if re.search(pattern, text, re.I):
            level = candidate
            break

    # Branch detection
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
        if re.search(pattern, text, re.I)
    ]

    # Equivalent experience alternatives
    alternatives = []

    if re.search(
        r"\b(equivalent experience|equivalent practical experience|equivalent work experience)\b",
        text,
        re.I,
    ):
        alternatives.append("equivalent experience")
    if level == "none" and not branches and not alternatives:
        return None

    return {
    "level": level,
    "branches": branches,
    "alternatives": alternatives,
}


HUMAN_LANGUAGES = {
    "english",
    "hindi",
    "telugu",
    "tamil",
    "kannada",
    "malayalam",
    "urdu",
    "marathi",
    "bengali",
    "gujarati",
    "punjabi",
    "french",
    "german",
    "spanish",
    "japanese",
    "chinese",
    "korean",
    "arabic",
    "portuguese",
    "russian",
}


def _extract_languages(lines: list[str]) -> list[str]:
    """Extract human languages from explicitly language-related lines."""

    found = []

    for line in lines:
        text = line.lower()

        for language in HUMAN_LANGUAGES:
            if re.search(
                rf"\b{re.escape(language)}\b",
                text,
            ):
                found.append(language)

    return sorted(set(found))

def _extract_soft_skills(lines: list[str]) -> list[str]:
    """Extract configured soft skills from JD lines."""

    found = set()

    for line in lines:
        for sentence in _split_sentences(line):
            items, _ = extract_items(sentence)

            for item in items:
                if isinstance(item, dict):
                    for skill in item.get("any_of", []):
                        if skill_type(skill) == "soft":
                            found.add(skill)

                elif skill_type(item) == "soft":
                    found.add(item)

    return sorted(found)


def _extract_job_conditions(lines: list[str]) -> dict:
    """Extract all job conditions without treating them as skills."""

    result = {
        "location": None,
        "work_mode": None,
        "employment_type": None,
        "notice_period": None,
        "shift": None,
    }

    current_field = None

    heading_map = {
        "location": "location",
        "work location": "location",
        "job location": "location",
        "work mode": "work_mode",
        "work arrangement": "work_mode",
        "employment type": "employment_type",
        "job type": "employment_type",
        "notice period": "notice_period",
        "shift": "shift",
        "working hours": "shift",
    }

    patterns = {
        "location": re.compile(
            r"\b(?:location|based in|work location)\s*[:\-]?\s*(.+)",
            re.I,
        ),
        "work_mode": re.compile(
            r"\b(remote|hybrid|on[- ]site|onsite|work from home)\b",
            re.I,
        ),
        "employment_type": re.compile(
            r"\b(full[- ]time|part[- ]time|contract|internship|"
            r"permanent|temporary)\b",
            re.I,
        ),
        "notice_period": re.compile(
            r"\b(\d+\s*(?:days?|weeks?|months?)\s*notice)\b",
            re.I,
        ),
        "shift": re.compile(
            r"\b(day shift|night shift|rotational shifts?|"
            r"rotating shifts?|US shift|UK shift)\b",
            re.I,
        ),
    }

    for raw_line in lines:
        line = raw_line.strip()

        if not line:
            continue

        if line.startswith("__HEADING__:"):
            heading = line.replace("__HEADING__:", "").strip().lower()
            current_field = heading_map.get(heading)
            continue

        if current_field:
            match = patterns[current_field].search(line)

            if match:
                result[current_field] = match.group(1).strip()
            else:
                result[current_field] = line.strip(" :-")

            current_field = None
            continue

        # Check every condition on the line; do not stop at the first match.
        for field, pattern in patterns.items():
            match = pattern.search(line)

            if match and result[field] is None:
                value = (
                    match.group(1).strip()
                    if field == "location"
                    else match.group(0).strip()
                )
                result[field] = value

    return result


def _clean_other(lines: list[str]) -> list[str]:
    """Keep leftover non-skill requirements as display-only checklist items."""

    cleaned = []

    for line in lines:
        value = line.strip(" .;:-")

        if value and value not in cleaned:
            cleaned.append(value)

    return cleaned


def _is_company_information(line: str) -> bool:
    """Identify company marketing or benefits text that should be discarded."""

    return bool(
        re.search(
            r"\b(we offer|we provide|our benefits|our mission|"
            r"our vision|about our company|competitive salary|"
            r"health insurance|paid time off|employee benefits)\b",
            line,
            re.I,
        )
    )


# -------------------------------------------------------------------
# 8. Certification extraction
# -------------------------------------------------------------------

def _extract_certifications(
    lines: list[str],
    assume_certification: bool = False,
) -> list[str]:
    """Extract certification statements from classified JD lines."""

    certifications = []

    for line in lines:
        for sentence in _split_sentences(line):
            if (
                not assume_certification
                and not CERTIFICATION_CUES.search(sentence)
            ):
                continue

            cleaned = re.sub(
                r"^(required\s+)?certifications?\s*:\s*",
                "",
                sentence,
                flags=re.I,
            )

            cleaned = re.sub(
                r"^(required\s+)?certified\s+in\s+",
                "",
                cleaned,
                flags=re.I,
            )

            cleaned = cleaned.strip(" .;:-")

            if cleaned:
                certifications.append(cleaned)

    return list(dict.fromkeys(certifications))


def _classified_experience_and_certifications(parts):
    """Separate required and preferred experience and certifications."""

    required_experience = []
    preferred_experience = []
    required_certifications = []
    preferred_certifications = []

    sources = [
        ("header", parts["header"], False),
        ("required", parts["required"], False),
        ("preferred", parts["preferred"], False),
        ("experience", parts.get("experience", []), False),
        ("certifications", parts.get("certifications", []), True),
        (
            "preferred_certifications",
            parts.get("preferred_certifications", []),
            True,
        ),
    ]

    for section, lines, certification_section in sources:
        default = (
            "preferred"
            if section in {"preferred", "preferred_certifications"}
            else "required"
        )

        for line in lines:
            for sentence in _split_sentences(line):
                target = _cue_section(sentence, default)

                # Only classify genuine experience requirements.
                if _has_experience_requirement(sentence):
                    if target == "preferred":
                        preferred_experience.append(sentence)
                    else:
                        required_experience.append(sentence)

                # Keep certification classification unchanged.
                if (
                    certification_section
                    or CERTIFICATION_CUES.search(sentence)
                ):
                    if target == "preferred":
                        preferred_certifications.append(sentence)
                    else:
                        required_certifications.append(sentence)

    return (
        required_experience,
        preferred_experience,
        required_certifications,
        preferred_certifications,
    )


# -------------------------------------------------------------------
# 9. Skill categorization and deduplication
# -------------------------------------------------------------------

def _item_skills(item: Any) -> set[str]:
    """Return all canonical skills represented by an item."""

    if isinstance(item, dict):
        return {
            canon(skill)
            for skill in item.get("any_of", [])
        }

    return {canon(str(item))}


def _item_key(item: Any) -> tuple[str, ...]:
    """Create a stable key for individual skills and OR groups."""

    if isinstance(item, dict):
        return (
            "any_of",
            *sorted(canon(skill) for skill in item["any_of"]),
        )

    return (canon(str(item)),)


def _clean_items(
    items: list[Any],
    excluded_skills: set[str] | None = None,
) -> list[Any]:
    """Canonicalize and deduplicate parsed requirements."""

    excluded_skills = excluded_skills or set()

    cleaned = []
    seen = set()
    seen_skills = set()

    for item in items:
        if isinstance(item, dict):
            alternatives = list(
                dict.fromkeys(
                    canon(skill)
                    for skill in item["any_of"]
                )
            )

            alternatives = [
                skill
                for skill in alternatives
                if skill not in excluded_skills
                and skill not in seen_skills
            ]

            if not alternatives:
                continue

            if len(alternatives) == 1:
                normalized = alternatives[0]
            else:
                normalized = {"any_of": alternatives}

        else:
            normalized = canon(str(item))

            if normalized in excluded_skills:
                continue

            if normalized in seen_skills:
                continue

        key = _item_key(normalized)

        if key in seen:
            continue

        seen.add(key)
        seen_skills.update(_item_skills(normalized))
        cleaned.append(normalized)

    return cleaned


def _separate_soft_skills(
    items: list[Any],
    technical_items: list[Any],
    soft_skills: list[str],
) -> None:
    """Keep soft skills outside technical scoring."""

    for item in items:
        if isinstance(item, dict):
            alternatives = item["any_of"]

            soft = [
                skill
                for skill in alternatives
                if skill_type(skill) == "soft"
            ]

            technical = [
                skill
                for skill in alternatives
                if skill_type(skill) != "soft"
            ]

            soft_skills.extend(soft)

            if len(technical) == len(alternatives):
                technical_items.append(item)
            else:
                technical_items.extend(technical)

        elif skill_type(item) == "soft":
            soft_skills.append(item)

        else:
            technical_items.append(item)


# -------------------------------------------------------------------
# 10. Main JD parser
# -------------------------------------------------------------------

def parse_jd(
    text: str,
    use_llm: bool = False,
) -> JDResult:
    """Parse a job description into the agreed structured output."""

    parts = split_jd(text)

    title = _extract_title(parts["header"])

    normalized_title = re.sub(
        r"[\W_]+", " ", title
    ).strip().casefold()

    required_items = []
    preferred_items = []

    required_education_lines = []
    preferred_education_lines = []

    required_other = []
    preferred_other = []

    unresolved = []
    unresolved_skill_bullets = []

    # Keep responsibilities from the dedicated section.
    responsibilities = []

    for line in parts["responsibilities"]:
        responsibilities.extend(_split_sentences(line))

    # Extract configured soft skills from explicit soft-skill and
    # additional-requirement sections.
    soft_skills = _extract_soft_skills(
        parts["soft_skills"] + parts["other"]
    )

    known_skills = set(skill_patterns())

    # Job conditions may appear anywhere in the JD.
    condition_lines = (
        parts["job_conditions"]
        + parts["header"]
        + parts["required"]
        + parts["preferred"]
        + parts["other"]
    )

    job_conditions = _extract_job_conditions(condition_lines)

    # Explicit language section.
    required_languages = _extract_languages(parts["languages"])

    # Process requirements and header lines.
    processing_sections = [
        ("header", parts["header"]),
        ("required", parts["required"]),
        ("preferred", parts["preferred"]),
        ("education", parts["education"]),
        ("other", parts["other"]),
    ]

    for section_name, lines in processing_sections:
        for line in lines:
            for sentence in _split_sentences(line):

                # Skip only the exact title already extracted.
                normalized_sentence = re.sub(
                    r"[\W_]+", " ", sentence
                ).strip().casefold()

                if (
                    section_name == "header"
                    and normalized_title
                    and normalized_sentence == normalized_title
                ):
                    continue

                if _is_company_information(sentence):
                    continue

                # Capture responsibility statements wherever they appear.
                if _is_responsibility(sentence):
                    responsibilities.append(sentence)
                    continue

                target = _cue_section(
                    sentence,
                    "preferred" if section_name == "preferred" else "required",
                )

                # Ignore job-condition statements for scoring.
                if any(
                    re.search(pattern, sentence, re.I)
                    for pattern in (
                        r"\b(remote|hybrid|on[- ]site|onsite|work from home)\b",
                        r"\b(full[- ]time|part[- ]time|contract|internship)\b",
                        r"\b\d+\s*(?:days?|weeks?|months?)\s*notice\b",
                        r"\b(day shift|night shift|rotational shifts?|rotating shifts?)\b",
                    )
                ):
                    continue

                # Certifications have their own category.
                if CERTIFICATION_CUES.search(sentence):
                    continue

                # Education is classified independently.
                if EDUCATION_CUES.search(sentence):
                    if target == "preferred":
                        preferred_education_lines.append(sentence)
                    else:
                        required_education_lines.append(sentence)

                items, found = extract_items(sentence)

                if found:
                    known_items = []

                    for item in items:
                        if isinstance(item, dict):
                            known_group = [
                                skill
                                for skill in item["any_of"]
                                if skill in known_skills
                            ]

                            if known_group:
                                known_items.append({
                                    "any_of": known_group
                                })

                        elif item in known_skills:
                            known_items.append(item)

                    if known_items:
                        if target == "preferred":
                            preferred_items.extend(known_items)
                        else:
                            required_items.extend(known_items)

                    elif section_name in {"required", "preferred"}:
                        if not (
                            EDUCATION_CUES.search(sentence)
                            or _has_experience_requirement(sentence)
                        ):
                            unresolved_skill_bullets.append(sentence)

                elif not (
                    EDUCATION_CUES.search(sentence)
                    or _has_experience_requirement(sentence)
                ):
                    if section_name in {"required", "preferred"}:
                        unresolved_skill_bullets.append(sentence)

                    if section_name in {"required", "other"}:
                        required_other.append(sentence)
                    elif section_name == "preferred":
                        preferred_other.append(sentence)
                    elif section_name == "header":
                        unresolved.append(sentence)

    # Separate required/preferred experience and certifications.
    (
        required_experience_lines,
        preferred_experience_lines,
        required_certification_lines,
        preferred_certification_lines,
    ) = _classified_experience_and_certifications(parts)

    required_certifications = _extract_certifications(
        required_certification_lines,
        assume_certification=True,
    )

    preferred_certifications = _extract_certifications(
        preferred_certification_lines,
        assume_certification=True,
    )

    # Education from the dedicated education heading is required by default,
    # unless an explicit preferred cue overrides it.
    for line in parts["education"]:
        target = _cue_section(line, "required")

        if target == "preferred":
            preferred_education_lines.append(line)
        else:
            required_education_lines.append(line)

    # Route soft skills out of technical skill requirements.
    technical_required = []
    technical_preferred = []

    _separate_soft_skills(
        required_items,
        technical_required,
        soft_skills,
    )

    _separate_soft_skills(
        preferred_items,
        technical_preferred,
        soft_skills,
    )

    # Deduplicate required skills first.
    clean_required = _clean_items(technical_required)

    required_skills = set()

    for item in clean_required:
        required_skills.update(_item_skills(item))

    # Remove required skills from preferred skills.
    clean_preferred = _clean_items(
        technical_preferred,
        excluded_skills=required_skills,
    )

    # Languages from the explicit language section.
    preferred_languages = []

    required_group = {
        "skills": clean_required,
        "experience": _experience(required_experience_lines),
        "education": _education(required_education_lines),
        "certifications": required_certifications,
        "languages": required_languages,
        "other": _clean_other(required_other),
    }

    preferred_group = {
        "skills": clean_preferred,
        "experience": _experience(preferred_experience_lines),
        "education": _education(preferred_education_lines),
        "certifications": preferred_certifications,
        "languages": preferred_languages,
        "other": _clean_other(preferred_other),
    }

    # Debug output to verify extraction before creating JDResult.
    print("DEBUG responsibilities:", responsibilities)
    print("DEBUG soft skills:", soft_skills)
    print("DEBUG conditions:", job_conditions)

    return JDResult(
        title=title,
        required=required_group,
        preferred=preferred_group,
        soft_skills=sorted(set(soft_skills)),
        responsibilities=list(dict.fromkeys(responsibilities)),
        job_conditions=job_conditions,
        unresolved_bullets=list(dict.fromkeys(unresolved)),
        unresolved_skill_bullets=list(
            dict.fromkeys(unresolved_skill_bullets)
        ),
        llm_added_skills=[],
    )
