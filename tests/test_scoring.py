import pytest

from app.core.category_weights import score_category_weights


PAIR_ANSWERS = {"q1": "A", "q2": "A", "q3": "A", "q4": "D", "q5": "D", "q6": "D", "q7": "D"}


def test_seven_question_scoring_consistency_and_expected_evidence():
    first = score_category_weights(PAIR_ANSWERS)
    second = score_category_weights(PAIR_ANSWERS)
    assert first == second
    assert first.raw_scores == {
        "accommodation": 1.0, "restaurants": 5.0, "flights": 1.0,
        "attractions": 16.0, "local_mobility": 2.5,
    }
    assert len(first.explanations) == 7


def test_invalid_answer_and_incomplete_payload_are_rejected():
    with pytest.raises(ValueError, match="Exactly seven"):
        score_category_weights({"q1": "A"})
    answers = dict(PAIR_ANSWERS, q1="Z")
    with pytest.raises(ValueError, match="Invalid answer"):
        score_category_weights(answers)
