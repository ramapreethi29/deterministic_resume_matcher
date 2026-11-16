
"""Pydantic v2 schemas used by parsing, extraction, and API boundaries."""

from __future__ import annotations

from typing import Optional,Any,Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AnyOfItem(BaseModel):
    """One requirement satisfied by any listed alternative."""

    model_config = ConfigDict(extra="forbid")

    any_of: list[str] = Field(min_length=2)


class EducationRequirement(BaseModel):
    """Normalized education requirement."""

    model_config = ConfigDict(extra="forbid")

    level: str = "none"
    branches: list[str] = Field(default_factory=list)
    alternatives: list[str] = Field(default_factory=list)


class ExperienceRequirement(BaseModel):
    """Experience requirement expressed in months."""

    model_config = ConfigDict(extra="forbid")

    min_months: int = Field(default=0, ge=0)
    max_months: Optional[int] = Field(default=None, ge=0)
    domain: Optional[str] = None

    @model_validator(mode="after")
    def validate_experience_range(self):
        if (
            self.max_months is not None
            and self.max_months < self.min_months
        ):
            raise ValueError(
                "Maximum experience cannot be less than minimum experience."
            )
        return self


class RequirementGroup(BaseModel):
    """Shared structure for required and preferred requirements."""

    model_config = ConfigDict(extra="forbid")

    skills: list[str | AnyOfItem] = Field(default_factory=list)
    experience: Optional[ExperienceRequirement] = None
    education: Optional[EducationRequirement] = None
    certifications: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    other: list[str] = Field(default_factory=list)


class JobConditions(BaseModel):
    """Non-scored job conditions."""

    model_config = ConfigDict(extra="forbid")

    location: Optional[str] = None
    work_mode: Optional[str] = None
    employment_type: Optional[str] = None
    notice_period: Optional[str] = None
    shift: Optional[str] = None


class JDResult(BaseModel):
    """Complete structured output from JD parsing."""

    model_config = ConfigDict(extra="forbid")

    title: str = ""
    required: RequirementGroup = Field(default_factory=RequirementGroup)
    preferred: RequirementGroup = Field(default_factory=RequirementGroup)

    soft_skills: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    job_conditions: JobConditions = Field(default_factory=JobConditions)

    unresolved_bullets: list[str] = Field(default_factory=list)
    unresolved_skill_bullets: list[str] = Field(default_factory=list)
    llm_added_skills: list[str] = Field(default_factory=list)


class ExtractionResult(BaseModel):
    """Validated output from the LLM skill extraction fallback."""

    model_config = ConfigDict(extra="forbid")

    skills: list[str] = Field(default_factory=list)


class AnalyzeRequest(BaseModel):
    """Input accepted by the analysis API."""

    resume_json: dict
    jd_text: str


class AnalyzeResponse(BaseModel):
    """Analysis API response."""

    model_config = ConfigDict(extra="allow")


class MatchEvidence(BaseModel):
    """Evidence supporting a matched skill."""

    model_config = ConfigDict(extra="forbid")

    sections: list[str] = Field(default_factory=list)
    level: Literal["demonstrated", "claimed", "mentioned"]


class MatchItem(BaseModel):
    """One JD requirement and its resume match result."""

    model_config = ConfigDict(extra="forbid")

    item: Any
    kind: Literal["skill", "experience", "education", "certification"]
    status: Literal["matched", "partial", "missing"]

    match_type: Optional[
        Literal["exact", "alias", "implied", "any_of", "semantic"]
    ] = None

    matched_with: list[str] = Field(default_factory=list)
    similarity: Optional[float] = Field(default=None, ge=0, le=100)

    evidence: Optional[MatchEvidence] = None
    detail: Optional[dict[str, Any]] = None


class SideResult(BaseModel):
    """Results for either required or preferred JD requirements."""

    model_config = ConfigDict(extra="forbid")

    total: int = Field(default=0, ge=0)
    matched: list[MatchItem] = Field(default_factory=list)
    partial: list[MatchItem] = Field(default_factory=list)
    missing: list[MatchItem] = Field(default_factory=list)


class ScoreSideBreakdown(BaseModel):
    """Scoring breakdown for one requirement group."""

    model_config = ConfigDict(extra="forbid")

    weight: float = Field(ge=0, le=1)
    credit: float = Field(default=0, ge=0)
    total: int = Field(default=0, ge=0)
    pct: float = Field(default=0, ge=0, le=1)
    points: float = Field(default=0, ge=0)


class ScoreBreakdown(BaseModel):
    """Required and preferred scoring breakdown."""

    model_config = ConfigDict(extra="forbid")

    required: ScoreSideBreakdown
    preferred: ScoreSideBreakdown


class SoftSkillsReport(BaseModel):
    """Soft skills displayed without affecting the score."""

    model_config = ConfigDict(extra="forbid")

    jd: list[str] = Field(default_factory=list)
    resume: list[str] = Field(default_factory=list)
    scored: Literal[False] = False


class OtherRequirement(BaseModel):
    """Non-scored requirement that needs manual verification."""

    model_config = ConfigDict(extra="forbid")

    item: str
    status: Literal["unverified"] = "unverified"


class MatchMeta(BaseModel):
    """Metadata about the matching process."""

    model_config = ConfigDict(extra="forbid")

    engine_version: str = "0.1.0"
    skills_dictionary_version: int = 2
    llm_used: bool = False
    semantic_matches: int = 0
    invariants_ok: bool = True
    processing_ms: int = 0


class MatchReport(BaseModel):
    """Complete resume-to-JD matching report."""

    model_config = ConfigDict(extra="forbid")

    score: int = Field(ge=0, le=100)
    score_breakdown: ScoreBreakdown

    required: SideResult
    preferred: SideResult

    soft_skills: SoftSkillsReport = Field(default_factory=SoftSkillsReport)
    other_requirements: list[OtherRequirement] = Field(default_factory=list)
    job_conditions: JobConditions = Field(default_factory=JobConditions)

    gaps: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)

    meta: MatchMeta = Field(default_factory=MatchMeta)

    @model_validator(mode="after")
    def validate_report_invariants(self):
        errors = []

        for name in ("required", "preferred"):
            side = getattr(self, name)

            actual_count = (
                len(side.matched)
                + len(side.partial)
                + len(side.missing)
            )

            if actual_count != side.total:
                errors.append(
                    f"{name}: total is {side.total}, "
                    f"but result entries add up to {actual_count}."
                )

        if errors:
            self.meta.invariants_ok = False
            self.warnings.extend(errors)

        return self
