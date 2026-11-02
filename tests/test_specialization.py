from app.core.simulator import generate_simulated_users, matched_pair


def test_matched_pair_has_same_answers_and_categories_but_distinct_deeper_preferences():
    user_a, user_b = matched_pair(generate_simulated_users())
    assert user_a.answers == user_b.answers
    assert user_a.initial_state.category_weights == user_b.initial_state.category_weights
    assert user_a.initial_state.category_weights["attractions"] >= 0.30
    assert user_a.initial_state.criterion_weights != user_b.initial_state.criterion_weights
    assert user_a.initial_state.liked_attributes != user_b.initial_state.liked_attributes
    assert {user_a.initial_state.activity_preferences.preference_scope,
            user_b.initial_state.activity_preferences.preference_scope} == {"specialized", "general"}


def test_five_user_cohort_contains_both_required_comparison_patterns():
    users = generate_simulated_users()
    assert len(users) == 5

    first, second, third = users[:3]
    assert first.initial_state.category_weights == second.initial_state.category_weights
    assert second.initial_state.category_weights == third.initial_state.category_weights

    shared = set(first.initial_state.preferred_attraction_themes) & set(
        second.initial_state.preferred_attraction_themes
    )
    assert len(shared) >= 2
    assert first.initial_state.activity_preferences.preference_scope == "specialized"
    assert second.initial_state.activity_preferences.preference_scope == "general"

    assert third.initial_state.activity_preferences.preference_scope == "specialized"
    assert first.initial_state.preferred_attraction_themes != third.initial_state.preferred_attraction_themes
