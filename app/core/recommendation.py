from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

from app.models.schemas import Attraction, RecommendationItem, RecommendationResult, UserProfile


DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "attractions.csv"
AVERAGE_SPEED_KMH = 30.0


def load_attractions() -> list[Attraction]:
    frame = pd.read_csv(DATA_FILE)
    records = []
    for row in frame.to_dict(orient="records"):
        row["themes"] = str(row["themes"]).split("|")
        records.append(Attraction(**row))
    return records


def haversine_km(a: Attraction, b: Attraction) -> float:
    radius = 6371.0
    lat1, lat2 = math.radians(a.latitude), math.radians(b.latitude)
    dlat = lat2 - lat1
    dlon = math.radians(b.longitude - a.longitude)
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return radius * 2 * math.asin(math.sqrt(h))


def approximate_transfer_minutes(a: Attraction, b: Attraction) -> float:
    return haversine_km(a, b) / AVERAGE_SPEED_KMH * 60.0


def _attribute_score(candidate: Attraction, liked: set[str], specialized: bool) -> float:
    if not liked:
        return 0.5
    overlap = len(liked.intersection(candidate.themes))
    score = overlap / len(liked) if specialized else min(1.0, overlap / 2.0)
    return float(score)


def _candidate_features(candidate: Attraction, profile: UserProfile, selected: list[Attraction]) -> tuple[dict[str, float], float | None]:
    state = profile.initial_state
    liked = set(state.preferred_attraction_themes or state.liked_attributes)
    specialized = state.activity_preferences.preference_scope == "specialized"
    attribute = _attribute_score(candidate, liked, specialized)
    rating = max(0.0, min(1.0, (candidate.rating - 3.0) / 2.0))
    budget = max(0.0, min(1.0, 1.0 - candidate.estimated_cost / 40.0))
    if selected:
        used = {theme for item in selected for theme in item.themes}
        diversity = len(set(candidate.themes) - used) / max(1, len(candidate.themes))
        transfer = approximate_transfer_minutes(selected[-1], candidate)
        compactness = max(0.0, 1.0 - transfer / 60.0)
    else:
        diversity, transfer, compactness = 1.0, None, 1.0
    return {
        "attribute_match": attribute,
        "rating": rating,
        "budget": budget,
        "diversity": float(diversity),
        "compactness": float(compactness),
    }, transfer


def recommend(profile: UserProfile, candidates: list[Attraction] | None = None) -> RecommendationResult:
    candidates = list(candidates or load_attractions())
    prefs = profile.initial_state.activity_preferences
    default_counts = {"low": 2, "moderate": 3, "high": 5}
    requested_count = prefs.preferred_attraction_count or default_counts[prefs.activity_density]
    weights = profile.initial_state.criterion_weights
    selected_items: list[RecommendationItem] = []
    selected_attractions: list[Attraction] = []
    remaining = list(candidates)
    while remaining and len(selected_items) < requested_count:
        choices: list[tuple[float, str, Attraction, dict[str, float], float | None]] = []
        for candidate in remaining:
            features, transfer = _candidate_features(candidate, profile, selected_attractions)
            if transfer is not None and prefs.max_transfer_minutes is not None and transfer > prefs.max_transfer_minutes:
                continue
            utility = sum(weights[key] * features[key] for key in weights)
            choices.append((utility, candidate.id, candidate, features, transfer))
        if not choices:
            break
        utility, _, candidate, features, transfer = max(choices, key=lambda row: (row[0], row[1]))
        selected_items.append(RecommendationItem(
            attraction=candidate, feature_scores=features, utility=utility,
            approximate_transfer_minutes=transfer,
        ))
        selected_attractions.append(candidate)
        remaining = [item for item in remaining if item.id != candidate.id]
    if selected_attractions:
        unique = {theme for item in selected_attractions for theme in item.themes}
        total_theme_mentions = sum(len(item.themes) for item in selected_attractions)
        diversity = len(unique) / max(1, total_theme_mentions)
        transfers = [approximate_transfer_minutes(a, b) for a, b in zip(selected_attractions, selected_attractions[1:])]
        compactness = 1.0 - min(1.0, (sum(transfers) / len(transfers)) / 60.0) if transfers else 1.0
    else:
        diversity = compactness = 0.0
    return RecommendationResult(
        user_id=profile.user_id,
        selected=selected_items,
        plan_features={"diversity": diversity, "compactness": compactness},
        total_utility=sum(item.utility for item in selected_items),
        constraint_note=(
            "Transfer constraints use straight-line Haversine distance converted with an assumed 30 km/h speed; "
            "they are approximations, not road-network travel times."
        ),
    )


def compare_profiles(user_a: UserProfile, user_b: UserProfile) -> dict:
    result_a, result_b = recommend(user_a), recommend(user_b)
    ids_a = [item.attraction.id for item in result_a.selected]
    ids_b = [item.attraction.id for item in result_b.selected]
    return {
        "identical_category_weights": user_a.initial_state.category_weights == user_b.initial_state.category_weights,
        "different_criterion_weights": user_a.initial_state.criterion_weights != user_b.initial_state.criterion_weights,
        "different_semantics": user_a.initial_state.liked_attributes != user_b.initial_state.liked_attributes,
        "recommendations_differ": ids_a != ids_b,
        "user_a": result_a.model_dump(mode="json"),
        "user_b": result_b.model_dump(mode="json"),
    }
