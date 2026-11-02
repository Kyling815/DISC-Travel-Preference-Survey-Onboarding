from __future__ import annotations

from app.core.questionnaire import validate_answers


DISC_ORDER = ["D", "I", "S", "C"]


def score_disc(answers: dict[str, str]) -> tuple[dict[str, float], str | None]:
    counts = {key: 0.0 for key in DISC_ORDER}
    for question, option in validate_answers(answers):
        if question["group"] == "disc" and option.get("disc"):
            counts[option["disc"]] += 1.0
    total = sum(counts.values())
    scores = {key: value / total if total else 0.0 for key, value in counts.items()}
    dominant = max(DISC_ORDER, key=lambda key: (scores[key], -DISC_ORDER.index(key))) if total else None
    return scores, dominant
