from __future__ import annotations

from app.core.category_weights import score_category_weights
from app.core.criterion_weights import estimate_criterion_weights
from app.core.semantic_preferences import derive_semantics
from app.models.schemas import ActivityPreferences, CriterionInput, InitialState, UserMetadata, UserProfile


def build_user_profile(
    user_id: str,
    answers: dict[str, str],
    preferences: CriterionInput,
    *,
    liked_attributes: list[str] | None = None,
    disliked_attributes: list[str] | None = None,
    is_simulated: bool = False,
    seed: int | None = None,
) -> UserProfile:
    category = score_category_weights(answers)
    criterion = estimate_criterion_weights(preferences)
    derived_liked, derived_disliked = derive_semantics(preferences)
    state = InitialState(
        category_weights=category.category_weights,
        criterion_weights=criterion.criterion_weights,
        liked_attributes=liked_attributes if liked_attributes is not None else derived_liked,
        disliked_attributes=disliked_attributes if disliked_attributes is not None else derived_disliked,
        preferred_attraction_themes=preferences.preferred_attraction_themes,
        activity_preferences=ActivityPreferences(
            preference_scope=preferences.preference_scope,
            activity_density=preferences.activity_density,
            preferred_attraction_count=preferences.preferred_attraction_count,
            max_transfer_minutes=preferences.max_transfer_minutes,
        ),
    )
    return UserProfile(
        user_id=user_id,
        answers=answers,
        disc_profile=category.disc_scores,
        initial_state=state,
        metadata=UserMetadata(is_simulated=is_simulated, seed=seed),
    )
