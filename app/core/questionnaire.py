from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parents[1] / "data"


@lru_cache(maxsize=1)
def load_questionnaire() -> dict:
    with (DATA_DIR / "questions.json").open(encoding="utf-8") as handle:
        data = json.load(handle)
    if len(data.get("questions", [])) != 7:
        raise RuntimeError("Questionnaire configuration must contain exactly seven questions")
    return data


def public_questions() -> list[dict]:
    return load_questionnaire()["questions"]


@lru_cache(maxsize=1)
def load_onboarding_quiz() -> dict:
    with (DATA_DIR / "onboarding_quiz.json").open(encoding="utf-8") as handle:
        data = json.load(handle)
    if len(data.get("questions", [])) != 7:
        raise RuntimeError("Onboarding v2 configuration must contain exactly seven questions")
    return data


def validate_answers(answers: dict[str, str]) -> list[tuple[dict, dict]]:
    questions = load_questionnaire()["questions"]
    expected = {q["id"] for q in questions}
    if set(answers) != expected:
        missing, extra = sorted(expected - set(answers)), sorted(set(answers) - expected)
        raise ValueError(f"Exactly seven answers are required; missing={missing}, unsupported={extra}")
    selected = []
    for question in questions:
        option = next((o for o in question["options"] if o["id"] == answers[question["id"]]), None)
        if option is None:
            valid = [o["id"] for o in question["options"]]
            raise ValueError(f"Invalid answer {answers[question['id']]} for {question['id']}; valid={valid}")
        selected.append((question, option))
    return selected
