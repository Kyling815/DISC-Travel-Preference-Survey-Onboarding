from __future__ import annotations

import json
from pathlib import Path

from app.core.evaluation import evaluation_summary
from app.core.recommendation import compare_profiles
from app.core.simulator import matched_pair
from scripts.generate_users import OUTPUT_DIR, export_users


def run() -> dict:
    users = export_users()
    user_a, user_b = matched_pair(users)
    comparison = compare_profiles(user_a, user_b)
    summary = evaluation_summary(users)
    (OUTPUT_DIR / "recommendation_comparison.json").write_text(
        json.dumps(comparison, indent=2), encoding="utf-8"
    )
    (OUTPUT_DIR / "evaluation_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    category_rows = "\n".join(
        f"- {u.user_id}: max={max(u.initial_state.category_weights.values()):.6f}, "
        f"normalization_error={abs(sum(u.initial_state.category_weights.values()) - 1):.3e}"
        for u in users
    )
    criterion_rows = "\n".join(
        f"- {u.user_id} ({u.initial_state.activity_preferences.preference_scope}): "
        f"{json.dumps(u.initial_state.criterion_weights)}, error={abs(sum(u.initial_state.criterion_weights.values()) - 1):.3e}"
        for u in users
    )
    names_a = [item["attraction"]["name"] for item in comparison["user_a"]["selected"]]
    names_b = [item["attraction"]["name"] for item in comparison["user_b"]["selected"]]
    report = f"""# DISC–Travel Onboarding Evaluation Report

All users and attractions in this report are synthetic.

## A. Category Weight Validation

Generated users: {len(users)}. Threshold-valid: {summary['threshold_valid_count']} ({summary['threshold_valid_percentage']:.1f}%).

{category_rows}

## B. Criterion Weight Validation

Criterion weights are independent of category weights. Scope labels describe breadth and do not replace features.

{criterion_rows}

## C. Matched-User Comparison

- Users: {user_a.user_id} and {user_b.user_id}
- Shared questionnaire-derived category vector: `{json.dumps(user_a.initial_state.category_weights)}`
- Criterion vectors differ: {comparison['different_criterion_weights']}
- Semantic preferences differ: {comparison['different_semantics']}
- Specialized recommendations: {names_a}
- General recommendations: {names_b}
- Recommendation sets differ: {comparison['recommendations_differ']}
- Full utility and feature breakdown: `recommendation_comparison.json`

## D. Limitations

- DISC-to-travel mappings are heuristic; no scientifically validated personality inference is claimed.
- Synthetic users are not actual users.
- Synthetic candidates cannot demonstrate real-world recommendation accuracy.
- Geographic transfer values use Haversine distance and assumed speed, not road-network travel time.
- This is not a trained DQN policy.
- Results demonstrate representation and ranking behavior, not empirical proof of better personalization.
"""
    (OUTPUT_DIR / "evaluation_report.md").write_text(report, encoding="utf-8")
    return summary


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2))
