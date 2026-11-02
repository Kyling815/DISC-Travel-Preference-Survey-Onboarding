from __future__ import annotations

import numpy as np

from app.core.prompt_parser import analyze_prompt
from app.core.questionnaire import load_onboarding_quiz
from app.models.schemas import (
    CATEGORY_ORDER, CRITERION_ORDER, OnboardingFinalizeRequest, PTSInitialState,
    PTSOnboardingProfile,
)


DISC_ORDER = ["D", "I", "S", "C"]


def _normalize(values: dict[str, float], order: list[str]) -> dict[str, float]:
    raw = np.array([float(values[key]) for key in order], dtype=float)
    if np.any(raw < 0) or raw.sum() <= 0:
        raise ValueError("Preference vector must be nonnegative with a positive sum")
    normalized = raw / raw.sum()
    return dict(zip(order, normalized.tolist()))


def _blend(parts: list[tuple[float, dict[str, float]]], order: list[str]) -> dict[str, float]:
    result = np.zeros(len(order), dtype=float)
    for coefficient, vector in parts:
        result += coefficient * np.array([vector[key] for key in order], dtype=float)
    result /= result.sum()
    return dict(zip(order, result.tolist()))


def _score_disc(answers: dict[str, str], quiz: dict) -> tuple[dict[str, float], str | None, list[dict]]:
    expected = {"q1", "q2", "q3"}
    if set(answers) != expected:
        raise ValueError(f"disc_answers must contain exactly {sorted(expected)}")
    counts = {key: 0.0 for key in DISC_ORDER}
    explanations = []
    by_id = {question["id"]: question for question in quiz["questions"]}
    for question_id in sorted(expected):
        question = by_id[question_id]
        option = next((item for item in question["options"] if item["id"] == answers[question_id]), None)
        if option is None:
            raise ValueError(f"Invalid answer {answers[question_id]} for {question_id}")
        counts[option["disc"]] += 1.0
        explanations.append({"question_id": question_id, "answer_id": option["id"], "disc": option["disc"]})
    scores = {key: value / 3.0 for key, value in counts.items()}
    maximum = max(scores.values())
    leaders = [key for key in DISC_ORDER if scores[key] == maximum]
    return scores, leaders[0] if len(leaders) == 1 else None, explanations


def finalize_onboarding(payload: OnboardingFinalizeRequest) -> PTSOnboardingProfile:
    quiz = load_onboarding_quiz()
    prompt_analysis = analyze_prompt(payload.prompt)
    disc_scores, dominant_disc, disc_explanations = _score_disc(payload.disc_answers, quiz)

    allocation = _normalize(payload.category_allocation, CATEGORY_ORDER)
    preserved = {key: (0.5 if key in payload.preserved_categories else 0.0) for key in CATEGORY_ORDER}
    if payload.category_override is not None:
        category_weights = _normalize(payload.category_override, CATEGORY_ORDER)
        category_source = "user_override"
    else:
        category_weights = _blend([
            (0.25, prompt_analysis.provisional_category_weights),
            (0.55, allocation),
            (0.20, preserved),
        ], CATEGORY_ORDER)
        category_source = "prompt_quiz_fusion"

    q6 = next(question for question in quiz["questions"] if question["id"] == "q6")
    expected_tradeoffs = {item["id"] for item in q6["tradeoffs"]}
    if set(payload.criterion_tradeoffs) != expected_tradeoffs:
        raise ValueError(f"criterion_tradeoffs must contain exactly {sorted(expected_tradeoffs)}")
    tradeoff_raw = {key: 1.0 for key in CRITERION_ORDER}
    tradeoff_explanations = []
    for tradeoff in q6["tradeoffs"]:
        side = payload.criterion_tradeoffs[tradeoff["id"]]
        criterion = tradeoff[side]["criterion"]
        tradeoff_raw[criterion] += 1.0
        tradeoff_explanations.append({"tradeoff_id": tradeoff["id"], "choice": side, "criterion": criterion})
    tradeoff_weights = _normalize(tradeoff_raw, CRITERION_ORDER)

    activity_raw = {key: 1.0 for key in CRITERION_ORDER}
    if payload.activity.preference_scope == "specialized":
        activity_raw["attribute_match"] += 1.0
    else:
        activity_raw["diversity"] += 1.0
    if payload.activity.max_transfer_minutes is not None:
        activity_raw["compactness"] += 1.0
    activity_weights = _normalize(activity_raw, CRITERION_ORDER)
    if payload.criterion_override is not None:
        criterion_weights = _normalize(payload.criterion_override, CRITERION_ORDER)
        criterion_source = "user_override"
    else:
        criterion_weights = _blend([
            (0.30, prompt_analysis.provisional_criterion_weights),
            (0.60, tradeoff_weights),
            (0.10, activity_weights),
        ], CRITERION_ORDER)
        criterion_source = "prompt_quiz_fusion"

    confidence = {
        "disc": 0.75 if dominant_disc is not None and max(disc_scores.values()) == 1.0 else 0.60,
        "category_weights": 0.95 if payload.category_override else 0.85,
        "criterion_weights": 0.95 if payload.criterion_override else 0.78,
        "semantic_preferences": prompt_analysis.confidence["semantic_preferences"],
    }
    state = PTSInitialState(
        disc_profile=disc_scores,
        dominant_disc=dominant_disc,
        category_weights=category_weights,
        criterion_weights=criterion_weights,
        semantic_preferences={
            "preferred_attraction_themes": prompt_analysis.evidence.preferred_attraction_themes,
            "preferred_food_attributes": prompt_analysis.evidence.preferred_food_attributes,
            "liked_attributes": prompt_analysis.evidence.liked_attributes,
            "disliked_attributes": prompt_analysis.evidence.disliked_attributes,
        },
        activity_preferences=payload.activity,
        trip_constraints=prompt_analysis.constraints,
    )
    return PTSOnboardingProfile(
        user_id=payload.user_id,
        initial_state=state,
        confidence=confidence,
        provenance={
            "prompt_used": True,
            "quiz_version": quiz["version"],
            "quiz_completed": True,
            "user_confirmed": payload.user_confirmed,
            "category_source": category_source,
            "criterion_source": criterion_source,
            "fusion_coefficients": {
                "category": {"prompt": 0.25, "allocation": 0.55, "preservation_tradeoff": 0.20},
                "criterion": {"prompt": 0.30, "tradeoffs": 0.60, "activity": 0.10},
                "disc_to_preference_contribution": 0.0,
            },
            "prompt_explanations": prompt_analysis.evidence.explanations,
            "disc_explanations": disc_explanations,
            "criterion_tradeoff_explanations": tradeoff_explanations,
        },
        metadata={
            "source": "disc_travel_onboarding_v2",
            "feedback_count": 0,
            "ready_for_pts": payload.user_confirmed,
        },
    )
