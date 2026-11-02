from __future__ import annotations

import numpy as np

from app.core.disc_scoring import score_disc
from app.core.questionnaire import load_questionnaire, validate_answers
from app.models.schemas import CATEGORY_ORDER, ScoreResult


def score_category_weights(answers: dict[str, str]) -> ScoreResult:
    selected = validate_answers(answers)
    configured_order = load_questionnaire()["category_order"]
    if configured_order != CATEGORY_ORDER:
        raise RuntimeError("Configured category order does not match the application schema")
    raw = np.ones(len(CATEGORY_ORDER), dtype=float)
    explanations: list[dict] = []
    for question, option in selected:
        vector = np.array([float(option.get("evidence", {}).get(k, 0.0)) for k in CATEGORY_ORDER])
        if np.any(vector < 0):
            raise ValueError(f"Negative evidence is not allowed in {question['id']}")
        raw += vector
        explanations.append({
            "question_id": question["id"], "question": question["text"],
            "answer_id": option["id"], "answer": option["text"],
            "contribution": dict(zip(CATEGORY_ORDER, vector.tolist())),
        })
    weights = raw / raw.sum()
    disc_scores, dominant_disc = score_disc(answers)
    return ScoreResult(
        raw_scores=dict(zip(CATEGORY_ORDER, raw.tolist())),
        category_weights=dict(zip(CATEGORY_ORDER, weights.tolist())),
        disc_scores=disc_scores,
        dominant_disc=dominant_disc,
        explanations=explanations,
    )
