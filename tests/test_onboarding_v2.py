import pytest
from fastapi.testclient import TestClient

from app.core.onboarding import finalize_onboarding
from app.core.prompt_parser import analyze_prompt
from app.main import app
from app.models.schemas import OnboardingFinalizeRequest


PROMPT = (
    "Tôi muốn lên 1 kế hoạch đi du lịch Đà Nẵng từ Tp.HCM, với ngân sách "
    "9.000.000 VND cho 2 người, 3 ngày 2 đêm, ưu tiên các địa điểm liên quan "
    "đến văn hóa-lịch sử, đồng thời trải nghiệm nhiều đặc sản địa phương"
)


def payload(**changes):
    data = {
        "user_id": "new_user_001",
        "prompt": PROMPT,
        "disc_answers": {"q1": "D", "q2": "D", "q3": "B"},
        "category_allocation": {
            "accommodation": 10, "restaurants": 30, "flights": 10,
            "attractions": 38, "local_mobility": 12,
        },
        "preserved_categories": ["attractions", "restaurants"],
        "criterion_tradeoffs": {
            "theme_vs_rating": "left", "match_vs_budget": "right",
            "specialization_vs_diversity": "left", "quality_vs_compactness": "right",
        },
        "activity": {
            "preference_scope": "specialized", "activity_density": "high",
            "preferred_attraction_count": 4, "preferred_food_experience_count": 4,
            "max_transfer_minutes": 30,
        },
        "user_confirmed": True,
    }
    data.update(changes)
    return data


def test_prompt_parser_extracts_constraints_and_explicit_preferences():
    result = analyze_prompt(PROMPT)
    assert result.constraints.origin == "TP.HCM"
    assert result.constraints.destination == "Đà Nẵng"
    assert result.constraints.total_budget_vnd == 9_000_000
    assert result.constraints.traveler_count == 2
    assert result.constraints.duration_days == 3
    assert result.constraints.duration_nights == 2
    assert {"culture", "history"}.issubset(result.evidence.preferred_attraction_themes)
    assert "local_specialties" in result.evidence.preferred_food_attributes
    assert result.provisional_category_weights["attractions"] > result.provisional_category_weights["flights"]
    assert result.provisional_criterion_weights["budget"] > result.provisional_criterion_weights["rating"]


def test_finalize_produces_normalized_pts_ready_state_with_provenance():
    result = finalize_onboarding(OnboardingFinalizeRequest(**payload()))
    assert sum(result.initial_state.category_weights.values()) == pytest.approx(1.0)
    assert sum(result.initial_state.criterion_weights.values()) == pytest.approx(1.0)
    assert result.initial_state.category_weights["attractions"] > result.initial_state.category_weights["flights"]
    assert result.initial_state.criterion_weights["attribute_match"] > result.initial_state.criterion_weights["rating"]
    assert result.metadata["ready_for_pts"] is True
    assert result.provenance["fusion_coefficients"]["disc_to_preference_contribution"] == 0.0


def test_disc_answers_do_not_change_category_or_criterion_weights():
    first = finalize_onboarding(OnboardingFinalizeRequest(**payload()))
    second = finalize_onboarding(OnboardingFinalizeRequest(**payload(
        disc_answers={"q1": "A", "q2": "A", "q3": "A"}
    )))
    assert first.initial_state.disc_profile != second.initial_state.disc_profile
    assert first.initial_state.category_weights == second.initial_state.category_weights
    assert first.initial_state.criterion_weights == second.initial_state.criterion_weights


def test_invalid_category_allocation_is_rejected():
    invalid = payload()
    invalid["category_allocation"]["attractions"] = 20
    with pytest.raises(ValueError, match="sum to 100"):
        OnboardingFinalizeRequest(**invalid)


def test_v2_api_workflow():
    client = TestClient(app)
    quiz = client.get("/onboarding/start-quiz")
    assert quiz.status_code == 200
    assert len(quiz.json()["questions"]) == 7
    analysis = client.post("/onboarding/prompt/analyze", json={"prompt": PROMPT})
    assert analysis.status_code == 200
    assert analysis.json()["constraints"]["destination"] == "Đà Nẵng"
    finalized = client.post("/onboarding/finalize", json=payload())
    assert finalized.status_code == 200
    assert finalized.json()["metadata"]["ready_for_pts"] is True
