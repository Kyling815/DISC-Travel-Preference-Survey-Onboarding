from __future__ import annotations

import json

from app.core.onboarding import finalize_onboarding
from app.models.schemas import OnboardingFinalizeRequest
from scripts.generate_users import OUTPUT_DIR


SAMPLE_PROMPT = (
    "Tôi muốn lên 1 kế hoạch đi du lịch Đà Nẵng từ Tp.HCM, với ngân sách "
    "9.000.000 VND cho 2 người, 3 ngày 2 đêm, ưu tiên các địa điểm liên quan "
    "đến văn hóa-lịch sử, đồng thời trải nghiệm nhiều đặc sản địa phương"
)


def run() -> dict:
    request = OnboardingFinalizeRequest(
        user_id="demo_new_user",
        prompt=SAMPLE_PROMPT,
        disc_answers={"q1": "D", "q2": "D", "q3": "B"},
        category_allocation={
            "accommodation": 10, "restaurants": 30, "flights": 10,
            "attractions": 38, "local_mobility": 12,
        },
        preserved_categories=["attractions", "restaurants"],
        criterion_tradeoffs={
            "theme_vs_rating": "left",
            "match_vs_budget": "right",
            "specialization_vs_diversity": "left",
            "quality_vs_compactness": "right",
        },
        activity={
            "preference_scope": "specialized",
            "activity_density": "high",
            "preferred_attraction_count": 4,
            "preferred_food_experience_count": 4,
            "max_transfer_minutes": 30,
        },
        user_confirmed=True,
    )
    profile = finalize_onboarding(request)
    OUTPUT_DIR.mkdir(exist_ok=True)
    destination = OUTPUT_DIR / "pts_initial_state_example.json"
    destination.write_text(profile.model_dump_json(indent=2), encoding="utf-8")
    return profile.model_dump(mode="json")


if __name__ == "__main__":
    result = run()
    print(json.dumps({
        "user_id": result["user_id"],
        "category_weights": result["initial_state"]["category_weights"],
        "criterion_weights": result["initial_state"]["criterion_weights"],
        "ready_for_pts": result["metadata"]["ready_for_pts"],
        "output": "outputs/pts_initial_state_example.json",
    }, indent=2))
