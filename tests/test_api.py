from fastapi.testclient import TestClient

from app.main import app
from tests.test_scoring import PAIR_ANSWERS


client = TestClient(app)


def test_health_questions_and_score_endpoints():
    assert client.get("/health").json()["status"] == "ok"
    assert len(client.get("/questions").json()["questions"]) == 7
    response = client.post("/onboarding/score", json={"answers": PAIR_ANSWERS})
    assert response.status_code == 200
    assert response.json()["category_weights"]["attractions"] >= 0.30


def test_simulation_comparison_and_evaluation_endpoints():
    response = client.post("/simulation/generate", json={"count": 5, "seed": 42, "max_attempts": 1000})
    assert response.status_code == 200
    assert len(response.json()["users"]) == 5
    comparison = client.post("/recommendations/compare", json={})
    assert comparison.status_code == 200
    assert comparison.json()["recommendations_differ"] is True
    summary = client.get("/evaluation/summary")
    assert summary.status_code == 200
    assert summary.json()["all_valid"] is True


def test_invalid_api_input_is_descriptive():
    response = client.post("/onboarding/score", json={"answers": {"q1": "Z"}})
    assert response.status_code == 422
    assert "seven answers" in response.json()["detail"]
