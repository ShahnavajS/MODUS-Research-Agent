import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_execute_pipeline_success(client: AsyncClient):
    # 1. Setup project & question
    p_res = await client.post(
        "/api/v1/projects",
        json={"name": "Retail AI Logistics", "research_topic": "Supply Chain AI", "industry": "Retail"},
    )
    p_id = p_res.json()["id"]

    q_res = await client.post(
        f"/api/v1/projects/{p_id}/questions",
        json={"question": "How is AI transforming retail store operations and inventory management?"},
    )
    q_id = q_res.json()["id"]

    # 2. Trigger research run
    run_res = await client.post(f"/api/v1/questions/{q_id}/runs", json={})
    assert run_res.status_code == 201
    run_id = run_res.json()["id"]
    assert run_res.json()["status"] == "queued"

    # 3. Execute research run
    exec_res = await client.post(f"/api/v1/runs/{run_id}/execute")
    assert exec_res.status_code == 200
    exec_data = exec_res.json()

    # 4. Assert status & completed timestamp
    assert exec_data["status"] == "completed"
    assert exec_data["started_at"] is not None
    assert exec_data["completed_at"] is not None
    assert exec_data["error_message"] is None

    # 5. Assert entity counts
    counts = exec_data["counts"]
    assert counts["sub_questions"] >= 3
    assert counts["sources"] >= 2
    assert counts["findings"] >= 2
    assert counts["evidence"] >= 2
    assert counts["conclusions"] >= 1


@pytest.mark.asyncio
async def test_completed_run_cannot_be_reexecuted(client: AsyncClient):
    p_res = await client.post("/api/v1/projects", json={"name": "Finance AI", "research_topic": "Banking"})
    p_id = p_res.json()["id"]
    q_res = await client.post(f"/api/v1/projects/{p_id}/questions", json={"question": "What is AI fraud detection ROI?"})
    q_id = q_res.json()["id"]
    run_res = await client.post(f"/api/v1/questions/{q_id}/runs", json={})
    run_id = run_res.json()["id"]

    # Execute once
    await client.post(f"/api/v1/runs/{run_id}/execute")

    # Try executing second time
    re_exec = await client.post(f"/api/v1/runs/{run_id}/execute")
    assert re_exec.status_code == 400
    assert "already completed" in re_exec.json()["detail"].lower()


@pytest.mark.asyncio
async def test_nonexistent_run_execute_returns_404(client: AsyncClient):
    random_uuid = str(uuid.uuid4())
    res = await client.post(f"/api/v1/runs/{random_uuid}/execute")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_different_questions_produce_input_dependent_results(client: AsyncClient):
    # Project 1: Healthcare AI
    p1 = await client.post("/api/v1/projects", json={"name": "Health AI", "research_topic": "Oncology AI"})
    q1 = await client.post(
        f"/api/v1/projects/{p1.json()['id']}/questions",
        json={"question": "How is generative AI improving diagnostic radiology precision?"},
    )
    r1 = await client.post(f"/api/v1/questions/{q1.json()['id']}/runs", json={})
    e1 = await client.post(f"/api/v1/runs/{r1.json()['id']}/execute")

    # Project 2: Manufacturing AI
    p2 = await client.post("/api/v1/projects", json={"name": "Manufacturing AI", "research_topic": "Robotics"})
    q2 = await client.post(
        f"/api/v1/projects/{p2.json()['id']}/questions",
        json={"question": "What computer vision models optimize assembly line quality control?"},
    )
    r2 = await client.post(f"/api/v1/questions/{q2.json()['id']}/runs", json={})
    e2 = await client.post(f"/api/v1/runs/{r2.json()['id']}/execute")

    # Verify both completed cleanly
    assert e1.json()["status"] == "completed"
    assert e2.json()["status"] == "completed"

    # Fetch details to ensure distinct results
    res1_detail = await client.get(f"/api/v1/runs/{r1.json()['id']}")
    res2_detail = await client.get(f"/api/v1/runs/{r2.json()['id']}")

    assert res1_detail.json()["id"] != res2_detail.json()["id"]
