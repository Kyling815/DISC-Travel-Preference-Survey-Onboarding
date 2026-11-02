from app.core.recommendation import compare_profiles, recommend
from app.core.simulator import generate_simulated_users, matched_pair


def test_specialized_and_general_recommendations_differ():
    user_a, user_b = matched_pair(generate_simulated_users())
    comparison = compare_profiles(user_a, user_b)
    assert comparison["identical_category_weights"]
    assert comparison["recommendations_differ"]
    specialized = user_a if user_a.initial_state.activity_preferences.preference_scope == "specialized" else user_b
    result = recommend(specialized)
    historical = {"history", "museum", "heritage", "architecture"}
    assert all(historical.intersection(item.attraction.themes) for item in result.selected)


def test_max_transfer_hard_constraint_is_enforced():
    user_a, _ = matched_pair(generate_simulated_users())
    result = recommend(user_a)
    maximum = user_a.initial_state.activity_preferences.max_transfer_minutes
    assert all(item.approximate_transfer_minutes is None or item.approximate_transfer_minutes <= maximum
               for item in result.selected)
    assert "Haversine" in result.constraint_note
