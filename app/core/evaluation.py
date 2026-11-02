from __future__ import annotations

from app.core.recommendation import compare_profiles
from app.core.simulator import matched_pair
from app.models.schemas import UserProfile


def evaluation_summary(users: list[UserProfile]) -> dict:
    pair_a, pair_b = matched_pair(users)
    comparison = compare_profiles(pair_a, pair_b)
    category_errors = [abs(sum(u.initial_state.category_weights.values()) - 1.0) for u in users]
    criterion_errors = [abs(sum(u.initial_state.criterion_weights.values()) - 1.0) for u in users]
    valid = [max(u.initial_state.category_weights.values()) >= 0.30 for u in users]
    return {
        "total_simulated_users": len(users),
        "threshold_valid_count": sum(valid),
        "threshold_valid_percentage": 100.0 * sum(valid) / len(users) if users else 0.0,
        "maximum_category_normalization_error": max(category_errors, default=0.0),
        "maximum_criterion_normalization_error": max(criterion_errors, default=0.0),
        "matched_pairs": 1,
        "matched_pair_user_ids": [pair_a.user_id, pair_b.user_id],
        "specialized_general_recommendations_differ": comparison["recommendations_differ"],
        "all_valid": all(valid) and comparison["recommendations_differ"],
    }
