from __future__ import annotations

import numpy as np

from app.models.schemas import CRITERION_ORDER, CriterionInput, CriterionResult


def estimate_criterion_weights(spec: CriterionInput) -> CriterionResult:
    if spec.criterion_override is not None:
        raw = np.array([spec.criterion_override[k] for k in CRITERION_ORDER], dtype=float)
        weights = raw / raw.sum()
        return CriterionResult(
            raw_scores=dict(zip(CRITERION_ORDER, raw.tolist())),
            criterion_weights=dict(zip(CRITERION_ORDER, weights.tolist())),
            explanations=["User-supplied criterion weights were validated and normalized."],
        )

    raw = np.ones(5, dtype=float)
    explanations = ["Positive unit prior applied to all criteria."]
    if spec.preferred_attraction_themes:
        raw[0] += 1.0
        explanations.append("Named themes add attribute-match evidence.")
    if spec.preference_scope == "specialized":
        raw[0] += 3.0
        explanations.append("Specialized scope emphasizes exact theme matching.")
    else:
        raw[3] += 3.0
        explanations.append("General scope emphasizes variety across themes.")
    raw[1] += float(spec.rating_priority)
    raw[2] += float(spec.budget_priority)
    explanations.extend(["Rating priority maps to rating.", "Budget priority maps to affordability."])
    if spec.mobility_preference == "compact":
        raw[4] += 4.0
        explanations.append("Compact mobility preference emphasizes geographic compactness.")
    elif spec.mobility_preference == "balanced":
        raw[4] += 2.0
        explanations.append("Balanced mobility adds moderate compactness evidence.")
    else:
        raw[4] += 0.5
        explanations.append("Flexible mobility adds only slight compactness evidence.")
    if spec.activity_density == "high":
        raw[3] += 1.5
        explanations.append("High activity density modestly favors varied plans; count remains a separate constraint.")
    elif spec.activity_density == "low":
        raw[0] += 0.5
        explanations.append("Low activity density modestly favors selectivity; count remains separate.")
    weights = raw / raw.sum()
    return CriterionResult(
        raw_scores=dict(zip(CRITERION_ORDER, raw.tolist())),
        criterion_weights=dict(zip(CRITERION_ORDER, weights.tolist())),
        explanations=explanations,
    )
