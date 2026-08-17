import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_golden_case_1_technology_transformation(client: AsyncClient):
    """Golden Test Case 1: Technology Transformation."""
    # 1. Project & Question
    p_res = await client.post("/api/v1/projects", json={"name": "Tech Eval", "research_topic": "Edge AI"})
    p_id = p_res.json()["id"]

    q_res = await client.post(f"/api/v1/projects/{p_id}/questions", json={"question": "What is the impact of Edge AI on industrial IoT latency?"})
    q_id = q_res.json()["id"]

    # 2. Run & Execute
    run_res = await client.post(f"/api/v1/questions/{q_id}/runs", json={})
    run_id = run_res.json()["id"]

    exec_res = await client.post(f"/api/v1/runs/{run_id}/execute")
    assert exec_res.status_code == 200

    # 3. Details & Traceability
    details = (await client.get(f"/api/v1/runs/{run_id}/details")).json()
    assert details["status"] == "completed"
    assert len(details["sub_questions"]) >= 1
    assert len(details["findings"]) >= 1
    assert len(details["conclusions"]) >= 1
    assert "Edge AI" in details["sub_questions"][0]["question"] or "industrial" in details["sub_questions"][0]["question"].lower()


@pytest.mark.asyncio
async def test_golden_case_2_healthcare_ai(client: AsyncClient):
    """Golden Test Case 2: Healthcare AI."""
    p_res = await client.post("/api/v1/projects", json={"name": "Healthcare Eval", "research_topic": "Clinical AI"})
    p_id = p_res.json()["id"]

    q_res = await client.post(f"/api/v1/projects/{p_id}/questions", json={"question": "How do diagnostic AI algorithms improve radiological screening accuracy?"})
    q_id = q_res.json()["id"]

    run_res = await client.post(f"/api/v1/questions/{q_id}/runs", json={})
    run_id = run_res.json()["id"]

    exec_res = await client.post(f"/api/v1/runs/{run_id}/execute")
    assert exec_res.status_code == 200

    details = (await client.get(f"/api/v1/runs/{run_id}/details")).json()
    assert details["status"] == "completed"
    assert "radiological" in details["sub_questions"][0]["question"].lower() or "diagnostic" in details["sub_questions"][0]["question"].lower()


@pytest.mark.asyncio
async def test_golden_case_3_financial_compliance(client: AsyncClient):
    """Golden Test Case 3: Financial Compliance."""
    p_res = await client.post("/api/v1/projects", json={"name": "Finance Eval", "research_topic": "Banking AML"})
    p_id = p_res.json()["id"]

    q_res = await client.post(f"/api/v1/projects/{p_id}/questions", json={"question": "What is the ROI of automated AML transaction monitoring in retail banking?"})
    q_id = q_res.json()["id"]

    run_res = await client.post(f"/api/v1/questions/{q_id}/runs", json={})
    run_id = run_res.json()["id"]

    exec_res = await client.post(f"/api/v1/runs/{run_id}/execute")
    assert exec_res.status_code == 200

    details = (await client.get(f"/api/v1/runs/{run_id}/details")).json()
    assert details["status"] == "completed"
    assert "aml" in details["sub_questions"][0]["question"].lower() or "banking" in details["sub_questions"][0]["question"].lower()
