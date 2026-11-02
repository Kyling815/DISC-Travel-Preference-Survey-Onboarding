from __future__ import annotations

from app.models.schemas import CriterionInput


def derive_semantics(spec: CriterionInput) -> tuple[list[str], list[str]]:
    liked = list(dict.fromkeys(theme.strip().lower() for theme in spec.preferred_attraction_themes if theme.strip()))
    disliked: list[str] = []
    if spec.max_transfer_minutes is not None or spec.mobility_preference == "compact":
        disliked.append("long_transfer")
    disliked.append("unrelated_attractions" if spec.preference_scope == "specialized" else "repetitive_activities")
    return liked, disliked
