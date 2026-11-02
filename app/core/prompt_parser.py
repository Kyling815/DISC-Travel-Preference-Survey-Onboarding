from __future__ import annotations

import re
import unicodedata

import numpy as np

from app.models.schemas import (
    CATEGORY_ORDER, CRITERION_ORDER, PromptAnalysis, PromptEvidence, TripConstraints,
)


def _ascii_fold(value: str) -> str:
    value = value.replace("Đ", "D").replace("đ", "d")
    return "".join(ch for ch in unicodedata.normalize("NFD", value) if unicodedata.category(ch) != "Mn").lower()


def _normalize(raw: np.ndarray, order: list[str]) -> dict[str, float]:
    values = raw / raw.sum()
    return dict(zip(order, values.tolist()))


def _canonical_location(value: str) -> str:
    cleaned = re.split(r"\b(?:voi|ngan sach|cho|trong|uu tien)\b", value, maxsplit=1)[0]
    cleaned = cleaned.strip(" ,.-")
    aliases = {
        "tp.hcm": "TP.HCM", "tphcm": "TP.HCM", "tp hcm": "TP.HCM",
        "ho chi minh": "TP.HCM", "sai gon": "TP.HCM", "da nang": "Đà Nẵng",
        "ha noi": "Hà Nội", "hue": "Huế", "hoi an": "Hội An",
    }
    return aliases.get(cleaned, cleaned.title()) if cleaned else ""


def _extract_constraints(prompt: str, folded: str) -> TripConstraints:
    travelers = re.search(r"(\d+)\s*(?:nguoi|khach)", folded)
    days_nights = re.search(r"(\d+)\s*ngay\s*(\d+)\s*dem", folded)
    days = days_nights or re.search(r"(\d+)\s*ngay", folded)
    nights = days_nights or re.search(r"(\d+)\s*dem", folded)
    budget = None
    budget_match = re.search(r"(?:ngan sach[^\d]{0,20})?(\d[\d.,]*)\s*(trieu|vnd|dong|d)\b", folded)
    if budget_match:
        numeric = budget_match.group(1)
        if budget_match.group(2) == "trieu":
            budget = int(float(numeric.replace(",", ".")) * 1_000_000)
        else:
            budget = int(re.sub(r"\D", "", numeric))

    origin = destination = None
    from_to = re.search(r"\btu\s+([^,]+?)\s+(?:den|toi)\s+([^,]+)", folded)
    destination_first = re.search(r"(?:di\s+du\s+lich|du\s+lich)\s+(.+?)\s+tu\s+([^,]+)", folded)
    if from_to:
        origin, destination = map(_canonical_location, from_to.groups())
    elif destination_first:
        destination, origin = map(_canonical_location, destination_first.groups())

    return TripConstraints(
        origin=origin or None,
        destination=destination or None,
        traveler_count=int(travelers.group(1)) if travelers else None,
        duration_days=int(days.group(1)) if days else None,
        duration_nights=int(days_nights.group(2)) if days_nights else (int(nights.group(1)) if nights else None),
        total_budget_vnd=budget,
    )


def analyze_prompt(prompt: str) -> PromptAnalysis:
    folded = _ascii_fold(prompt)
    category = np.ones(len(CATEGORY_ORDER), dtype=float)
    criterion = np.ones(len(CRITERION_ORDER), dtype=float)
    explanations: list[str] = []
    themes: list[str] = []
    food_attributes: list[str] = []
    liked: list[str] = []
    disliked: list[str] = []

    theme_keywords = {
        "culture": ["van hoa", "cultural"],
        "history": ["lich su", "historical"],
        "heritage": ["di san", "heritage"],
        "architecture": ["kien truc", "architecture"],
        "nature": ["thien nhien", "canh quan", "nature"],
        "museum": ["bao tang", "museum"],
        "entertainment": ["giai tri", "entertainment"],
        "landmark": ["bieu tuong", "landmark"],
    }
    for theme, keywords in theme_keywords.items():
        if any(keyword in folded for keyword in keywords):
            themes.append(theme)
    if themes:
        category[CATEGORY_ORDER.index("attractions")] += 4.0
        criterion[CRITERION_ORDER.index("attribute_match")] += 4.0
        liked.extend(themes)
        explanations.append(f"Chủ đề điểm tham quan được nêu rõ: {', '.join(themes)}.")

    food_keywords = {
        "local_food": ["am thuc dia phuong", "mon dia phuong", "local food"],
        "local_specialties": ["dac san", "specialties"],
        "street_food": ["duong pho", "street food"],
    }
    for attribute, keywords in food_keywords.items():
        if any(keyword in folded for keyword in keywords):
            food_attributes.append(attribute)
    if food_attributes:
        category[CATEGORY_ORDER.index("restaurants")] += 3.5
        liked.extend(food_attributes)
        explanations.append("Prompt thể hiện ưu tiên trải nghiệm ẩm thực hoặc đặc sản địa phương.")

    if any(word in folded for word in ["khach san", "luu tru", "resort", "homestay"]):
        category[CATEGORY_ORDER.index("accommodation")] += 2.5
        explanations.append("Prompt có yêu cầu rõ về lưu trú.")
    if any(word in folded for word in ["may bay", "chuyen bay", "flight"]):
        category[CATEGORY_ORDER.index("flights")] += 2.5
        explanations.append("Prompt có yêu cầu rõ về chuyến bay.")
    if any(word in folded for word in ["di chuyen noi thanh", "thue xe", "taxi", "xe buyt"]):
        category[CATEGORY_ORDER.index("local_mobility")] += 2.5
        explanations.append("Prompt có yêu cầu rõ về di chuyển địa phương.")

    constraints = _extract_constraints(prompt, folded)
    if constraints.total_budget_vnd is not None or "ngan sach" in folded or "tiet kiem" in folded:
        criterion[CRITERION_ORDER.index("budget")] += 3.0
        explanations.append("Ngân sách được nêu rõ nên budget sensitivity được tăng.")
    if any(word in folded for word in ["rating", "danh gia cao", "chat luong cao"]):
        criterion[CRITERION_ORDER.index("rating")] += 3.0
        explanations.append("Prompt nhấn mạnh đánh giá hoặc chất lượng.")
    if any(word in folded for word in ["da dang", "nhieu loai", "ket hop nhieu"]):
        criterion[CRITERION_ORDER.index("diversity")] += 3.0
        explanations.append("Prompt nêu rõ mong muốn đa dạng hoạt động.")
    if any(word in folded for word in ["gan nhau", "it di chuyen", "lich trinh gon"]):
        criterion[CRITERION_ORDER.index("compactness")] += 3.0
        explanations.append("Prompt nêu rõ mong muốn lịch trình tập trung.")
    elif constraints.duration_days is not None and constraints.duration_days <= 3:
        criterion[CRITERION_ORDER.index("compactness")] += 1.5
        explanations.append("Chuyến đi ngắn tạo bằng chứng suy luận mức vừa cho compactness.")

    negative_map = {
        "long_transfer": ["khong muon di xa", "tranh di xa"],
        "crowded": ["tranh dong duc", "khong dong duc"],
        "expensive": ["tranh dat", "khong qua dat"],
    }
    for attribute, keywords in negative_map.items():
        if any(keyword in folded for keyword in keywords):
            disliked.append(attribute)

    scope = "specialized" if themes and len(themes) <= 4 else "general"
    density = "high" if any(word in folded for word in ["nhieu dac san", "nhieu hoat dong", "cang nhieu cang tot"]) else "moderate"
    explicit_groups = int(bool(themes)) + int(bool(food_attributes)) + int(constraints.total_budget_vnd is not None)
    category_confidence = min(0.75, 0.30 + 0.15 * (int(bool(themes)) + int(bool(food_attributes))))
    criterion_confidence = min(0.70, 0.25 + 0.12 * explicit_groups)

    return PromptAnalysis(
        prompt=prompt,
        constraints=constraints,
        evidence=PromptEvidence(
            category_evidence=dict(zip(CATEGORY_ORDER, (category - 1.0).tolist())),
            criterion_evidence=dict(zip(CRITERION_ORDER, (criterion - 1.0).tolist())),
            preferred_attraction_themes=themes,
            preferred_food_attributes=food_attributes,
            liked_attributes=list(dict.fromkeys(liked)),
            disliked_attributes=disliked,
            inferred_preference_scope=scope,
            inferred_activity_density=density,
            explanations=explanations,
        ),
        provisional_category_weights=_normalize(category, CATEGORY_ORDER),
        provisional_criterion_weights=_normalize(criterion, CRITERION_ORDER),
        confidence={"category_weights": category_confidence, "criterion_weights": criterion_confidence, "semantic_preferences": min(0.9, 0.4 + 0.15 * explicit_groups)},
    )
