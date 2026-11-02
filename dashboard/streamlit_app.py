from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.llm_preprocessing import build_llm_preprocessing_payload
from app.core.onboarding import finalize_onboarding
from app.core.prompt_parser import analyze_prompt
from app.core.questionnaire import load_onboarding_quiz
from app.core.simulator import generate_simulated_users
from app.models.schemas import CATEGORY_ORDER, OnboardingActivityInput, OnboardingFinalizeRequest


def _display_text(value: str) -> str:
    """Repair legacy UTF-8 text that was previously decoded as Windows-1252."""
    try:
        return value.encode("cp1252").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value


st.set_page_config(page_title="Travel Preference Preprocessing", layout="wide")
st.title("Travel Preference Preprocessing")
st.caption(
    "Onboarding v2 chuyển prompt và câu trả lời xác nhận thành preference state có cấu trúc "
    "trước khi gửi sang mô hình LLM."
)

if "simulated_users" not in st.session_state:
    st.session_state.simulated_users = generate_simulated_users(count=5)

st.subheader("1. Phân tích prompt")
prompt = st.text_area(
    "Mô tả chuyến đi",
    value=(
        "Tôi muốn lên kế hoạch đi du lịch Đà Nẵng từ TP.HCM, với ngân sách "
        "9.000.000 VND cho 2 người, 3 ngày 2 đêm, ưu tiên các địa điểm "
        "văn hóa-lịch sử và trải nghiệm nhiều đặc sản địa phương."
    ),
    height=110,
)
if st.button("Phân tích prompt", type="primary"):
    st.session_state.prompt_analysis_v2 = analyze_prompt(prompt)
    st.session_state.pop("llm_payload_v2", None)

analysis = st.session_state.get("prompt_analysis_v2")
if analysis is None:
    st.info("Nhập mô tả và chọn “Phân tích prompt” để bắt đầu pipeline preprocessing.")
else:
    constraint_col, evidence_col = st.columns(2)
    with constraint_col:
        st.markdown("#### Ràng buộc chuyến đi")
        st.json(analysis.constraints.model_dump(mode="json"))
    with evidence_col:
        st.markdown("#### Evidence được trích xuất")
        st.json(analysis.evidence.model_dump(mode="json"))

    chart_col_a, chart_col_b = st.columns(2)
    with chart_col_a:
        st.plotly_chart(
            px.bar(
                x=list(analysis.provisional_category_weights),
                y=list(analysis.provisional_category_weights.values()),
                labels={"x": "Category", "y": "Weight"},
                title="Category prior từ prompt",
            ),
            use_container_width=True,
        )
    with chart_col_b:
        st.plotly_chart(
            px.bar(
                x=list(analysis.provisional_criterion_weights),
                y=list(analysis.provisional_criterion_weights.values()),
                labels={"x": "Criterion", "y": "Weight"},
                title="Criterion prior từ prompt",
            ),
            use_container_width=True,
        )

    quiz = load_onboarding_quiz()
    by_id = {question["id"]: question for question in quiz["questions"]}

    st.subheader("2. Xác nhận preference state")
    st.caption(
        "Prompt tạo prior ban đầu; các câu trả lời bên dưới xác nhận mức ưu tiên, "
        "trade-off và phạm vi specialized/general trước khi tạo input cho LLM."
    )

    with st.expander("Q1–Q3 · Phong cách ra quyết định DISC", expanded=False):
        disc_answers = {}
        for question_id in ["q1", "q2", "q3"]:
            question = by_id[question_id]
            labels = {
                option["id"]: f"{option['id']}. {_display_text(option['text'])}"
                for option in question["options"]
            }
            disc_answers[question_id] = st.radio(
                _display_text(question["text"]),
                list(labels),
                format_func=labels.get,
                key=f"v2_{question_id}",
            )

    st.markdown("#### Q4 · Phân bổ 100 điểm Category")
    suggested = {
        key: int(round(analysis.provisional_category_weights[key] * 100))
        for key in CATEGORY_ORDER
    }
    suggested[CATEGORY_ORDER[-1]] += 100 - sum(suggested.values())
    allocation = {}
    allocation_columns = st.columns(len(CATEGORY_ORDER))
    for column, category in zip(allocation_columns, CATEGORY_ORDER):
        allocation[category] = column.number_input(
            category,
            min_value=0,
            max_value=100,
            value=suggested[category],
            key=f"v2_alloc_{category}",
        )
    allocation_total = sum(allocation.values())
    st.caption(f"Tổng hiện tại: {allocation_total}/100")

    st.markdown("#### Q5 · Hai category cần bảo toàn")
    default_preserved = sorted(
        CATEGORY_ORDER,
        key=analysis.provisional_category_weights.get,
        reverse=True,
    )[:2]
    preserved = st.multiselect(
        "Chọn đúng hai category quan trọng nhất khi phải đánh đổi",
        CATEGORY_ORDER,
        default=default_preserved,
        max_selections=2,
        key="v2_preserved",
    )

    st.markdown("#### Q6 · Criterion trade-offs")
    tradeoff_answers = {}
    for tradeoff in by_id["q6"]["tradeoffs"]:
        labels = {
            "left": _display_text(tradeoff["left"]["text"]),
            "right": _display_text(tradeoff["right"]["text"]),
        }
        tradeoff_answers[tradeoff["id"]] = st.radio(
            tradeoff["id"].replace("_", " ").title(),
            ["left", "right"],
            format_func=labels.get,
            key=f"v2_tradeoff_{tradeoff['id']}",
            horizontal=True,
        )

    st.markdown("#### Q7 · Specialized/general và cấu trúc hoạt động")
    q7a, q7b, q7c = st.columns(3)
    scope_options = ["specialized", "general"]
    scope = q7a.selectbox(
        "Phạm vi preference",
        scope_options,
        index=scope_options.index(analysis.evidence.inferred_preference_scope),
        key="v2_scope",
        help="Specialized tập trung sâu vào chủ đề; general ưu tiên sự đa dạng.",
    )
    density_options = ["low", "moderate", "high"]
    density = q7b.selectbox(
        "Mật độ hoạt động",
        density_options,
        index=density_options.index(analysis.evidence.inferred_activity_density),
        key="v2_density",
    )
    attraction_count = q7c.number_input(
        "Số điểm tham quan", 1, 15, 4, key="v2_attraction_count"
    )
    q7d, q7e = st.columns(2)
    food_count = q7d.number_input(
        "Số trải nghiệm ẩm thực", 0, 15, 4, key="v2_food_count"
    )
    max_transfer = q7e.number_input(
        "Di chuyển tối đa (phút)", 5, 240, 30, key="v2_max_transfer"
    )
    confirmed = st.checkbox(
        "Tôi xác nhận preference state này để gửi sang LLM",
        key="v2_confirmed",
    )

    if st.button("Tạo LLM preprocessing payload", type="primary"):
        if allocation_total != 100:
            st.error("Q4 phải có tổng đúng 100 điểm.")
        elif len(preserved) != 2:
            st.error("Q5 phải chọn đúng hai category.")
        elif not confirmed:
            st.error("Cần xác nhận preference state trước khi tạo payload cho LLM.")
        else:
            request = OnboardingFinalizeRequest(
                user_id="interactive_user_v2",
                prompt=prompt,
                disc_answers=disc_answers,
                category_allocation=allocation,
                preserved_categories=preserved,
                criterion_tradeoffs=tradeoff_answers,
                activity=OnboardingActivityInput(
                    preference_scope=scope,
                    activity_density=density,
                    preferred_attraction_count=attraction_count,
                    preferred_food_experience_count=food_count,
                    max_transfer_minutes=max_transfer,
                ),
                user_confirmed=True,
            )
            profile = finalize_onboarding(request)
            st.session_state.pts_profile_v2 = profile
            st.session_state.llm_payload_v2 = build_llm_preprocessing_payload(profile, prompt)

    llm_payload = st.session_state.get("llm_payload_v2")
    if llm_payload is not None:
        st.subheader("3. Payload sẵn sàng cho LLM")
        st.success("Preprocessing hoàn tất. Hard constraints và preference state đã được tách rõ.")
        st.json(llm_payload)
        st.download_button(
            "Tải LLM preprocessing payload",
            json.dumps(llm_payload, ensure_ascii=False, indent=2),
            "llm_preprocessing_payload.json",
            "application/json",
        )

st.divider()
with st.expander("Mô phỏng kiểm chứng · 5 preference states", expanded=True):
    users = st.session_state.simulated_users
    archetype_labels = [
        "Heritage specialist",
        "Mixed generalist",
        "Nature specialist",
        "Food specialist",
        "Efficiency planner",
    ]
    rows = []
    for index, user in enumerate(users):
        state = user.initial_state
        rows.append({
            "user": user.user_id,
            "preference_state": archetype_labels[index],
            "scope": state.activity_preferences.preference_scope,
            "themes": ", ".join(state.preferred_attraction_themes),
            "dominant_category": max(state.category_weights, key=state.category_weights.get),
            "activity_density": state.activity_preferences.activity_density,
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    first, second, third = users[:3]
    shared_themes = sorted(
        set(first.initial_state.preferred_attraction_themes)
        & set(second.initial_state.preferred_attraction_themes)
    )
    check_a, check_b = st.columns(2)
    with check_a:
        st.markdown("**Đối chứng specialized ↔ general**")
        st.write(
            f"{first.user_id} và {second.user_id} có cùng category weights, "
            f"cùng hai preference `{', '.join(shared_themes)}`, nhưng scope lần lượt là "
            "`specialized` và `general`."
        )
    with check_b:
        st.markdown("**Đối chứng specialized ↔ specialized**")
        st.write(
            f"{first.user_id} và {third.user_id} cùng là `specialized` và có cùng category weights, "
            "nhưng tập theme chuyên sâu khác nhau."
        )

    long_rows = [
        {"user": user.user_id, "category": key, "weight": value}
        for user in users
        for key, value in user.initial_state.category_weights.items()
    ]
    st.plotly_chart(
        px.bar(
            pd.DataFrame(long_rows),
            x="user",
            y="weight",
            color="category",
            barmode="group",
            title="Category weights của 5 user mô phỏng",
        ),
        use_container_width=True,
    )
