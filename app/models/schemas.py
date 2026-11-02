from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


CATEGORY_ORDER = ["accommodation", "restaurants", "flights", "attractions", "local_mobility"]
CRITERION_ORDER = ["attribute_match", "rating", "budget", "diversity", "compactness"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AnswerSelection(StrictModel):
    answers: dict[str, str]


class ScoreResult(StrictModel):
    raw_scores: dict[str, float]
    category_weights: dict[str, float]
    disc_scores: dict[str, float]
    dominant_disc: str | None
    explanations: list[dict]


class CriterionInput(StrictModel):
    preferred_attraction_themes: list[str] = Field(default_factory=list)
    preference_scope: Literal["specialized", "general"] = "general"
    activity_density: Literal["low", "moderate", "high"] = "moderate"
    preferred_attraction_count: int | None = Field(default=None, ge=1, le=10)
    max_transfer_minutes: int | None = Field(default=None, ge=5, le=240)
    rating_priority: int = Field(default=3, ge=1, le=5)
    budget_priority: int = Field(default=3, ge=1, le=5)
    mobility_preference: Literal["compact", "balanced", "flexible"] = "balanced"
    criterion_override: dict[str, float] | None = None

    @field_validator("criterion_override")
    @classmethod
    def validate_override(cls, value: dict[str, float] | None) -> dict[str, float] | None:
        if value is None:
            return value
        if set(value) != set(CRITERION_ORDER):
            raise ValueError(f"criterion_override must contain exactly {CRITERION_ORDER}")
        if any(v < 0 for v in value.values()) or sum(value.values()) <= 0:
            raise ValueError("criterion_override values must be nonnegative with a positive sum")
        return value


class CriterionResult(StrictModel):
    raw_scores: dict[str, float]
    criterion_weights: dict[str, float]
    explanations: list[str]


class ActivityPreferences(StrictModel):
    preference_scope: Literal["specialized", "general"]
    activity_density: Literal["low", "moderate", "high"]
    preferred_attraction_count: int | None = Field(default=None, ge=1, le=10)
    max_transfer_minutes: int | None = Field(default=None, ge=5, le=240)


class InitialState(StrictModel):
    category_weights: dict[str, float]
    criterion_weights: dict[str, float]
    liked_attributes: list[str] = Field(default_factory=list)
    disliked_attributes: list[str] = Field(default_factory=list)
    preferred_attraction_themes: list[str] = Field(default_factory=list)
    activity_preferences: ActivityPreferences

    @model_validator(mode="after")
    def validate_vectors(self) -> "InitialState":
        for name, vector, expected in [
            ("category_weights", self.category_weights, CATEGORY_ORDER),
            ("criterion_weights", self.criterion_weights, CRITERION_ORDER),
        ]:
            if set(vector) != set(expected):
                raise ValueError(f"{name} must contain exactly {expected}")
            if any(v < 0 for v in vector.values()) or abs(sum(vector.values()) - 1.0) > 1e-6:
                raise ValueError(f"{name} must be nonnegative and sum to 1")
        return self


class UserMetadata(StrictModel):
    source: str = "disc_travel_onboarding"
    feedback_count: int = 0
    is_simulated: bool = False
    seed: int | None = None


class UserProfile(StrictModel):
    user_id: str
    answers: dict[str, str] = Field(default_factory=dict)
    disc_profile: dict[str, float] = Field(default_factory=dict)
    initial_state: InitialState
    metadata: UserMetadata


class InitialStateRequest(StrictModel):
    user_id: str
    answers: dict[str, str]
    preferences: CriterionInput
    liked_attributes: list[str] | None = None
    disliked_attributes: list[str] | None = None


class SimulationRequest(StrictModel):
    count: int = Field(default=5, ge=5, le=100)
    seed: int = 42
    max_attempts: int = Field(default=1000, ge=1, le=100000)


class CompareRequest(StrictModel):
    user_a: UserProfile | None = None
    user_b: UserProfile | None = None


class Attraction(StrictModel):
    id: str
    name: str
    themes: list[str]
    rating: float
    estimated_cost: float
    latitude: float
    longitude: float
    estimated_duration_minutes: int


class RecommendationItem(StrictModel):
    attraction: Attraction
    feature_scores: dict[str, float]
    utility: float
    approximate_transfer_minutes: float | None = None


class RecommendationResult(StrictModel):
    user_id: str
    selected: list[RecommendationItem]
    plan_features: dict[str, float]
    total_utility: float
    constraint_note: str


class TripConstraints(StrictModel):
    origin: str | None = None
    destination: str | None = None
    traveler_count: int | None = Field(default=None, ge=1, le=100)
    duration_days: int | None = Field(default=None, ge=1, le=365)
    duration_nights: int | None = Field(default=None, ge=0, le=365)
    total_budget_vnd: int | None = Field(default=None, ge=0)


class PromptEvidence(StrictModel):
    category_evidence: dict[str, float]
    criterion_evidence: dict[str, float]
    preferred_attraction_themes: list[str] = Field(default_factory=list)
    preferred_food_attributes: list[str] = Field(default_factory=list)
    liked_attributes: list[str] = Field(default_factory=list)
    disliked_attributes: list[str] = Field(default_factory=list)
    inferred_preference_scope: Literal["specialized", "general"]
    inferred_activity_density: Literal["low", "moderate", "high"]
    explanations: list[str] = Field(default_factory=list)


class PromptAnalysis(StrictModel):
    prompt: str
    constraints: TripConstraints
    evidence: PromptEvidence
    provisional_category_weights: dict[str, float]
    provisional_criterion_weights: dict[str, float]
    confidence: dict[str, float]


class PromptAnalysisRequest(StrictModel):
    prompt: str = Field(min_length=3, max_length=5000)


class OnboardingActivityInput(StrictModel):
    preference_scope: Literal["specialized", "general"]
    activity_density: Literal["low", "moderate", "high"]
    preferred_attraction_count: int | None = Field(default=None, ge=1, le=15)
    preferred_food_experience_count: int | None = Field(default=None, ge=0, le=15)
    max_transfer_minutes: int | None = Field(default=None, ge=5, le=240)


class OnboardingFinalizeRequest(StrictModel):
    user_id: str = Field(min_length=1, max_length=100)
    prompt: str = Field(min_length=3, max_length=5000)
    disc_answers: dict[str, str]
    category_allocation: dict[str, float]
    preserved_categories: list[str]
    criterion_tradeoffs: dict[str, Literal["left", "right"]]
    activity: OnboardingActivityInput
    category_override: dict[str, float] | None = None
    criterion_override: dict[str, float] | None = None
    user_confirmed: bool = False

    @field_validator("category_allocation")
    @classmethod
    def validate_allocation(cls, value: dict[str, float]) -> dict[str, float]:
        if set(value) != set(CATEGORY_ORDER):
            raise ValueError(f"category_allocation must contain exactly {CATEGORY_ORDER}")
        if any(v < 0 for v in value.values()) or abs(sum(value.values()) - 100.0) > 1e-6:
            raise ValueError("category_allocation must be nonnegative and sum to 100")
        return value

    @field_validator("preserved_categories")
    @classmethod
    def validate_preserved(cls, value: list[str]) -> list[str]:
        if len(value) != 2 or len(set(value)) != 2 or any(v not in CATEGORY_ORDER for v in value):
            raise ValueError("preserved_categories must contain exactly two distinct supported categories")
        return value

    @field_validator("category_override")
    @classmethod
    def validate_category_override(cls, value: dict[str, float] | None) -> dict[str, float] | None:
        return _validate_weight_override(value, CATEGORY_ORDER, "category_override")

    @field_validator("criterion_override")
    @classmethod
    def validate_criterion_v2_override(cls, value: dict[str, float] | None) -> dict[str, float] | None:
        return _validate_weight_override(value, CRITERION_ORDER, "criterion_override")


def _validate_weight_override(
    value: dict[str, float] | None, expected: list[str], field_name: str
) -> dict[str, float] | None:
    if value is None:
        return value
    if set(value) != set(expected):
        raise ValueError(f"{field_name} must contain exactly {expected}")
    if any(v < 0 for v in value.values()) or sum(value.values()) <= 0:
        raise ValueError(f"{field_name} must be nonnegative with a positive sum")
    return value


class PTSInitialState(StrictModel):
    disc_profile: dict[str, float]
    dominant_disc: str | None
    category_weights: dict[str, float]
    criterion_weights: dict[str, float]
    semantic_preferences: dict
    activity_preferences: OnboardingActivityInput
    trip_constraints: TripConstraints

    @model_validator(mode="after")
    def validate_preference_vectors(self) -> "PTSInitialState":
        for name, vector, expected in [
            ("category_weights", self.category_weights, CATEGORY_ORDER),
            ("criterion_weights", self.criterion_weights, CRITERION_ORDER),
        ]:
            if set(vector) != set(expected):
                raise ValueError(f"{name} must contain exactly {expected}")
            if any(v < 0 for v in vector.values()) or abs(sum(vector.values()) - 1.0) > 1e-6:
                raise ValueError(f"{name} must be nonnegative and sum to 1")
        return self


class PTSOnboardingProfile(StrictModel):
    schema_version: str = "2.0"
    user_id: str
    initial_state: PTSInitialState
    confidence: dict[str, float]
    provenance: dict
    metadata: dict
