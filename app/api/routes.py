from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.core.category_weights import score_category_weights
from app.core.criterion_weights import estimate_criterion_weights
from app.core.evaluation import evaluation_summary
from app.core.initial_state import build_user_profile
from app.core.onboarding import finalize_onboarding
from app.core.prompt_parser import analyze_prompt
from app.core.questionnaire import load_onboarding_quiz, public_questions
from app.core.recommendation import compare_profiles
from app.core.simulator import generate_simulated_users, matched_pair
from app.models.schemas import (
    AnswerSelection, CompareRequest, CriterionInput, InitialStateRequest,
    OnboardingFinalizeRequest, PromptAnalysisRequest, SimulationRequest,
)


router = APIRouter()


def _bad_request(error: Exception) -> HTTPException:
    return HTTPException(status_code=422, detail=str(error))


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "disc-travel-onboarding"}


@router.get("/questions")
def questions() -> dict:
    return {"questions": public_questions()}


@router.get("/onboarding/start-quiz")
def onboarding_start_quiz() -> dict:
    """Return the data-driven seven-step onboarding v2 definition."""
    return load_onboarding_quiz()


@router.post("/onboarding/prompt/analyze")
def onboarding_analyze_prompt(payload: PromptAnalysisRequest) -> dict:
    return analyze_prompt(payload.prompt).model_dump(mode="json")


@router.post("/onboarding/finalize")
def onboarding_finalize(payload: OnboardingFinalizeRequest) -> dict:
    try:
        return finalize_onboarding(payload).model_dump(mode="json")
    except ValueError as error:
        raise _bad_request(error) from error


@router.post("/onboarding/score")
def onboarding_score(payload: AnswerSelection) -> dict:
    try:
        return score_category_weights(payload.answers).model_dump(mode="json")
    except ValueError as error:
        raise _bad_request(error) from error


@router.post("/preferences/criterion")
def criterion(payload: CriterionInput) -> dict:
    return estimate_criterion_weights(payload).model_dump(mode="json")


@router.post("/initial-state")
def initial_state(payload: InitialStateRequest) -> dict:
    try:
        return build_user_profile(
            payload.user_id, payload.answers, payload.preferences,
            liked_attributes=payload.liked_attributes,
            disliked_attributes=payload.disliked_attributes,
        ).model_dump(mode="json")
    except ValueError as error:
        raise _bad_request(error) from error


@router.post("/simulation/generate")
def simulation_generate(payload: SimulationRequest, request: Request) -> dict:
    try:
        users = generate_simulated_users(payload.count, payload.seed, payload.max_attempts)
    except (ValueError, RuntimeError) as error:
        raise _bad_request(error) from error
    request.app.state.simulated_users = users
    return {"users": [user.model_dump(mode="json") for user in users]}


@router.get("/simulation/users")
def simulation_users(request: Request) -> dict:
    users = getattr(request.app.state, "simulated_users", None) or generate_simulated_users()
    request.app.state.simulated_users = users
    return {"users": [user.model_dump(mode="json") for user in users]}


@router.post("/recommendations/compare")
def recommendations_compare(payload: CompareRequest, request: Request) -> dict:
    if payload.user_a is not None and payload.user_b is not None:
        user_a, user_b = payload.user_a, payload.user_b
    elif payload.user_a is None and payload.user_b is None:
        users = getattr(request.app.state, "simulated_users", None) or generate_simulated_users()
        user_a, user_b = matched_pair(users)
    else:
        raise HTTPException(status_code=422, detail="Provide both user_a and user_b, or neither to use the matched pair")
    return compare_profiles(user_a, user_b)


@router.get("/evaluation/summary")
def summary(request: Request) -> dict:
    users = getattr(request.app.state, "simulated_users", None) or generate_simulated_users()
    return evaluation_summary(users)
