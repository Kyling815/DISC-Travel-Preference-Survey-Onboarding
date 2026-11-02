import pytest

from app.core.category_weights import score_category_weights
from app.core.criterion_weights import estimate_criterion_weights
from app.models.schemas import CriterionInput
from tests.test_scoring import PAIR_ANSWERS


def test_category_weights_are_nonnegative_and_normalized():
    weights = score_category_weights(PAIR_ANSWERS).category_weights
    assert all(value >= 0 for value in weights.values())
    assert sum(weights.values()) == pytest.approx(1.0)


def test_criterion_weights_are_independent_nonnegative_and_normalized():
    specialized = estimate_criterion_weights(CriterionInput(
        preference_scope="specialized", preferred_attraction_themes=["history"], mobility_preference="compact"
    )).criterion_weights
    general = estimate_criterion_weights(CriterionInput(
        preference_scope="general", preferred_attraction_themes=["nature"], activity_density="high"
    )).criterion_weights
    assert all(value >= 0 for value in specialized.values())
    assert sum(specialized.values()) == pytest.approx(1.0)
    assert sum(general.values()) == pytest.approx(1.0)
    assert specialized != general


def test_invalid_criterion_override_is_rejected():
    with pytest.raises(ValueError):
        CriterionInput(criterion_override={"rating": 1.0})
