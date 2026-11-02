from app.core.llm_preprocessing import build_llm_preprocessing_payload
from app.core.onboarding import finalize_onboarding
from app.models.schemas import OnboardingFinalizeRequest
from tests.test_onboarding_v2 import PROMPT, payload


def test_llm_payload_contains_confirmed_constraints_and_preference_state():
    profile = finalize_onboarding(OnboardingFinalizeRequest(**payload()))
    result = build_llm_preprocessing_payload(profile, PROMPT)

    assert result["preprocessing"]["ready_for_llm"] is True
    assert result["trip_constraints"]["destination"] == "Đà Nẵng"
    assert result["preference_state"]["activity_preferences"]["preference_scope"] == "specialized"
    assert result["preference_state"]["category_weights"] == profile.initial_state.category_weights
