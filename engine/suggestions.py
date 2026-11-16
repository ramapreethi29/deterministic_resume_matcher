
"""Generate generic resume improvement suggestions."""

def generate_suggestions(
    missing_required: list[str],
    missing_preferred: list[str],
) -> list[str]:
    """Generate practical suggestions based on missing skills."""

    missing_required = list(dict.fromkeys(missing_required))
    missing_preferred = list(dict.fromkeys(missing_preferred))

    suggestions = []

    if missing_required:
        skills = ", ".join(missing_required[:3])
        suggestions.append(
            f"Prioritize learning and practicing required skills such as {skills}. "
            "Build a small project to demonstrate your understanding."
        )

    if missing_preferred:
        skills = ", ".join(missing_preferred[:3])
        suggestions.append(
            f"Improve your profile by exploring preferred skills such as {skills}. "
            "Add practical experience through projects where possible."
        )

    suggestions.append(
        "Strengthen your resume with measurable project outcomes, "
        "specific technical contributions, and clear descriptions of your work."
    )

    return suggestions[:3]
