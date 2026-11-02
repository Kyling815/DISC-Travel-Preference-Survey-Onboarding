import json

import pytest

from app.core.initial_state import build_user_profile
from app.core.simulator import generate_simulated_users
from app.models.schemas import CriterionInput
from tests.test_scoring import PAIR_ANSWERS


def test_simulation_is_deterministic_complete_and_threshold_valid():
    first = generate_simulated_users(8, seed=123)
    second = generate_simulated_users(8, seed=123)
    assert [u.model_dump() for u in first] == [u.model_dump() for u in second]
    assert len(first) >= 5
    for user in first:
        assert max(user.initial_state.category_weights.values()) >= 0.30
        assert sum(user.initial_state.category_weights.values()) == pytest.approx(1.0)
        assert sum(user.initial_state.criterion_weights.values()) == pytest.approx(1.0)
        json.loads(user.model_dump_json())


def test_real_user_answers_are_not_mutated_to_meet_simulation_threshold():
    answers = {"q1":"A", "q2":"B", "q3":"C", "q4":"A", "q5":"B", "q6":"C", "q7":"E"}
    original = dict(answers)
    profile = build_user_profile("real", answers, CriterionInput())
    assert answers == original
    assert profile.answers == original
    assert profile.metadata.is_simulated is False
