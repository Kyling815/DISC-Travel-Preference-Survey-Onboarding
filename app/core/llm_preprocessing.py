from __future__ import annotations

from app.models.schemas import PTSOnboardingProfile


def build_llm_preprocessing_payload(
    profile: PTSOnboardingProfile,
    raw_prompt: str,
) -> dict:
    """Build a compact, explicit context object for a downstream LLM.

    The downstream model receives confirmed constraints and preference state instead
    of having to reinterpret the original onboarding conversation from scratch.
    """
    state = profile.initial_state
    return {
        "schema_version": "llm-preprocess-1.0",
        "user_id": profile.user_id,
        "raw_user_prompt": raw_prompt,
        "trip_constraints": state.trip_constraints.model_dump(mode="json"),
        "preference_state": {
            "category_weights": state.category_weights,
            "criterion_weights": state.criterion_weights,
            "semantic_preferences": state.semantic_preferences,
            "activity_preferences": state.activity_preferences.model_dump(mode="json"),
        },
        "confidence": profile.confidence,
        "preprocessing": {
            "source": "onboarding_v2",
            "user_confirmed": profile.provenance["user_confirmed"],
            "ready_for_llm": bool(profile.metadata["ready_for_pts"]),
            "category_source": profile.provenance["category_source"],
            "criterion_source": profile.provenance["criterion_source"],
        },
        "downstream_rules": [
            "Apply trip constraints before ranking recommendations.",
            "Do not invent preferences that are absent from semantic_preferences.",
            "Use specialized scope for focused recommendations and general scope for diversity.",
        ],
    }
