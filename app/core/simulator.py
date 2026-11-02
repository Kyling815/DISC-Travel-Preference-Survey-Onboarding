from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from app.core.category_weights import score_category_weights
from app.core.initial_state import build_user_profile
from app.models.schemas import CriterionInput, UserProfile


DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def _load_archetypes() -> list[dict]:
    with (DATA_DIR / "archetypes.json").open(encoding="utf-8") as handle:
        return json.load(handle)["profiles"]


def _preference_from_archetype(item: dict) -> CriterionInput:
    return CriterionInput(
        preferred_attraction_themes=item["themes"],
        preference_scope=item["scope"],
        activity_density=item["density"],
        preferred_attraction_count=item["count"],
        max_transfer_minutes=item["max_transfer"],
        rating_priority=item["rating"],
        budget_priority=item["budget"],
        mobility_preference=item["mobility"],
    )


def generate_simulated_users(count: int = 5, seed: int = 42, max_attempts: int = 1000) -> list[UserProfile]:
    if count < 5:
        raise ValueError("At least five simulated users are required")
    rng = np.random.default_rng(seed)
    archetypes = _load_archetypes()
    users: list[UserProfile] = []
    attempts = 0
    while len(users) < count and attempts < max_attempts:
        attempts += 1
        if len(users) < len(archetypes):
            item = archetypes[len(users)]
        else:
            base = archetypes[int(rng.integers(0, len(archetypes)))]
            item = dict(base)
            # Resample a valid answer sequence without modifying its resulting vector.
            questions = [f"q{i}" for i in range(1, 8)]
            choices = [list("ABCD")] * 3 + [list("ABCDE")] * 4
            item["answers"] = {q: str(rng.choice(opts)) for q, opts in zip(questions, choices)}
        scored = score_category_weights(item["answers"])
        if max(scored.category_weights.values()) < 0.30:
            continue
        user = build_user_profile(
            f"user_{len(users) + 1:03d}", item["answers"], _preference_from_archetype(item),
            is_simulated=True, seed=seed,
        )
        users.append(user)
    if len(users) < count:
        raise RuntimeError(
            f"Unable to generate {count} profiles satisfying max(category_weight) >= 0.30 "
            f"within {max_attempts} attempts (generated {len(users)})."
        )
    return users


def matched_pair(users: list[UserProfile] | None = None) -> tuple[UserProfile, UserProfile]:
    users = users or generate_simulated_users()
    for i, first in enumerate(users):
        for second in users[i + 1 :]:
            if (
                first.initial_state.category_weights == second.initial_state.category_weights
                and first.initial_state.activity_preferences.preference_scope != second.initial_state.activity_preferences.preference_scope
            ):
                return first, second
    raise ValueError("No specialized/general matched pair found")
