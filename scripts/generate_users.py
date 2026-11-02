from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from app.core.simulator import generate_simulated_users


OUTPUT_DIR = Path(__file__).resolve().parents[1] / "outputs"


def export_users(count: int = 5, seed: int = 42) -> list:
    users = generate_simulated_users(count=count, seed=seed)
    OUTPUT_DIR.mkdir(exist_ok=True)
    payload = [user.model_dump(mode="json") for user in users]
    (OUTPUT_DIR / "simulated_users.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    flat = []
    for user in users:
        state = user.initial_state
        flat.append({
            "user_id": user.user_id,
            "dominant_disc": max(user.disc_profile, key=user.disc_profile.get),
            "dominant_category": max(state.category_weights, key=state.category_weights.get),
            "preference_scope": state.activity_preferences.preference_scope,
            "activity_density": state.activity_preferences.activity_density,
            "liked_attributes": "|".join(state.liked_attributes),
            "disliked_attributes": "|".join(state.disliked_attributes),
        })
    pd.DataFrame(flat).to_csv(OUTPUT_DIR / "simulated_users.csv", index=False)
    pd.DataFrame([{"user_id": u.user_id, **u.initial_state.category_weights} for u in users]).to_csv(
        OUTPUT_DIR / "category_weights.csv", index=False
    )
    pd.DataFrame([{"user_id": u.user_id, **u.initial_state.criterion_weights} for u in users]).to_csv(
        OUTPUT_DIR / "criterion_weights.csv", index=False
    )
    return users


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    users = export_users(args.count, args.seed)
    # Keep console output ASCII-safe on Windows terminals whose inherited
    # encoding cannot represent non-ASCII characters in the project path.
    print(f"Exported {len(users)} deterministic users to the outputs directory")


if __name__ == "__main__":
    main()
