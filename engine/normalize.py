
"""Canonical skill normalization and boundary-safe regular-expression matching."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any


# Keep skills.json as the original baseline.
SKILLS_PATH = Path(__file__).with_name("skills.json")

# Extra safeguards if an alias is not listed in notes.ambiguous_aliases.
DEFAULT_AMBIGUOUS_ALIASES = {
    "go",
    "rest",
    "node",
    "spring",
    "auth",
}
EXCLUDED_PHRASES = {
    "gcp": [
        re.compile(
            r"\bgoogle\s+cloud\s+skills\s+boost\b",
            re.IGNORECASE,
        ),
    ],
}

@lru_cache(maxsize=1)
def load_dictionary() -> dict[str, Any]:
    """Load the canonical skill dictionary and implication map."""
    with SKILLS_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def _normalize_text(text: str) -> str:
    """Normalize casing and whitespace."""
    return re.sub(r"\s+", " ", str(text).lower().strip())


@lru_cache(maxsize=1)
def _ambiguous_aliases() -> frozenset[str]:
    """Load ambiguous aliases configured in the dictionary."""
    notes = load_dictionary().get("notes", {})
    configured = notes.get("ambiguous_aliases", []) if isinstance(notes, dict) else []

    aliases = set(DEFAULT_AMBIGUOUS_ALIASES)

    if isinstance(configured, (list, tuple, set)):
        aliases.update(
            _normalize_text(alias)
            for alias in configured
            if isinstance(alias, str) and alias.strip()
        )

    return frozenset(aliases)


@lru_cache(maxsize=1)
def _alias_index() -> dict[str, str]:
    """Map canonical names and aliases to canonical skill names."""
    data = load_dictionary()["skills"]
    index: dict[str, str] = {}

    for canonical, details in data.items():
        index[_normalize_text(canonical)] = canonical

        for alias in details.get("aliases", []):
            normalized = _normalize_text(alias)
            if normalized:
                index.setdefault(normalized, canonical)

    return index


def canon(text: str) -> str:
    """Normalize a skill using configured canonical names and aliases."""
    value = _normalize_text(text)
    return _alias_index().get(value, value)


def _pattern_for(alias: str) -> re.Pattern[str]:
    """Build a case-insensitive regex with safe technical boundaries."""
    parts = [_normalize_text(part) for part in alias.split()]
    escaped = r"\s+".join(re.escape(part) for part in parts if part)

    return re.compile(
    rf"(?<![\w.+#]){escaped}(?![\w+#]|\.(?=\w))",
    re.IGNORECASE,
)


@lru_cache(maxsize=1)
def skill_patterns() -> dict[str, list[tuple[str, re.Pattern[str]]]]:
    """Build patterns for every canonical skill and configured alias."""
    result: dict[str, list[tuple[str, re.Pattern[str]]]] = {}

    for canonical, details in load_dictionary()["skills"].items():
        aliases = list(
            dict.fromkeys(
                alias.strip()
                for alias in [canonical] + details.get("aliases", [])
                if isinstance(alias, str) and alias.strip()
            )
        )

        result[canonical] = [
            (alias, _pattern_for(alias))
            for alias in aliases
        ]

    return result


def skill_type(skill: str) -> str:
    """Return the configured category of a skill."""
    canonical = canon(skill)

    return (
        load_dictionary()["skills"]
        .get(canonical, {})
        .get("type", "technical")
    )


def _is_ambiguous_alias(alias: str) -> bool:
    """Check whether the matched alias is ambiguous."""
    return _normalize_text(alias) in _ambiguous_aliases()


def _sentences(text: str) -> list[str]:
    """Split prose into sentence-like units for contextual matching."""
    return [
        part.strip()
        for part in re.split(r"(?<=[.!?])\s+|\n+", text)
        if part.strip()
    ]

def _is_excluded_match(
    sentence: str,
    canonical: str,
    start: int,
    end: int,
) -> bool:
    """Reject only matches that overlap a known excluded phrase."""
    for pattern in EXCLUDED_PHRASES.get(canonical, []):
        for excluded_match in pattern.finditer(sentence):
            if (
                start < excluded_match.end()
                and end > excluded_match.start()
            ):
                return True

    return False

def _longest_non_overlapping_matches(
    sentence: str,
) -> list[tuple[str, str]]:
    """
    Find matches longest-first and discard overlapping shorter matches.

    For example, 'GitLab CI' is preferred over a separate 'GitLab'
    match occupying part of the same text span.
    """
    candidates: list[tuple[int, int, str, str]] = []

    for canonical, patterns in skill_patterns().items():
        for alias, pattern in patterns:
            for match in pattern.finditer(sentence):
                if _is_excluded_match(
        sentence,
        canonical,
        match.start(),
        match.end(),
    ):
                      continue

                candidates.append(
        (match.start(), match.end(), canonical, alias)
    )

    # Prefer longer aliases, then earlier positions for deterministic results.
    candidates.sort(
        key=lambda item: (
            -(item[1] - item[0]),
            item[0],
            item[2],
            item[3].lower(),
        )
    )

    accepted_spans: list[tuple[int, int]] = []
    accepted_matches: list[tuple[str, str]] = []

    for start, end, canonical, alias in candidates:
        overlaps = any(
            start < accepted_end and end > accepted_start
            for accepted_start, accepted_end in accepted_spans
        )

        if overlaps:
            continue

        accepted_spans.append((start, end))
        accepted_matches.append((canonical, alias))

    return accepted_matches


def find_skills(text: str, section: str | None = None) -> set[str]:
    """
    Find configured canonical skills in text.

    In a dedicated skills section, ambiguous aliases are accepted.
    In other named sections, an ambiguous alias is accepted only when
    another unambiguous technical skill occurs in the same sentence.

    When section is omitted, all configured aliases are accepted for
    backward compatibility with existing callers.
    """
    if not text:
        return set()

    section_name = _normalize_text(section or "")

    is_skills_section = section_name in {
        "skills",
        "technical skills",
        "core skills",
        "key skills",
    }

    found: set[str] = set()

    for sentence in _sentences(str(text)):
        sentence_matches = _longest_non_overlapping_matches(sentence)

        has_unambiguous_technical_skill = any(
            skill_type(canonical) == "technical"
            and not _is_ambiguous_alias(alias)
            for canonical, alias in sentence_matches
        )

        for canonical, alias in sentence_matches:
            should_reject_ambiguous = (
                section is not None
                and not is_skills_section
                and _is_ambiguous_alias(alias)
                and not has_unambiguous_technical_skill
            )

            if should_reject_ambiguous:
                continue

            found.add(canonical)

    return found
