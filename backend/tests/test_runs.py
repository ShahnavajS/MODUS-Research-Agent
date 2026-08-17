import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_and_get_research_run(client: AsyncClient):
    # 1. Create project & question
    p_res = await client.post("/api/v1/projects", json={"name": "Energy AI", "research_topic": "Grid AI"})
    p_id = p_res.json()["id"]

    q_res = await client.post(f"/api/v1/projects/{p_id}/questions", json={"question": "What is renewable energy forecasting accuracy?"})
    q_id = q_res.json()["id"]

    # 2. Trigger research run
    run_res = await client.post(f"/api/v1/questions/{q_id}/runs", json={"metadata_json": {"test": True}})
    assert run_res.status_code == 201
    run_data = run_res.json()
    assert run_data["question_id"] == q_id
    assert run_data["status"] == "queued"
    run_id = run_data["id"]

    # 3. Retrieve research run by ID
    get_run_res = await client.get(f"/api/v1/runs/{run_id}")
    assert get_run_res.status_code == 200
    assert get_run_res.json()["status"] == "queued"

    # 4. Retrieve run details by ID
    get_details_res = await client.get(f"/api/v1/runs/{run_id}/details")
    assert get_details_res.status_code == 200
    details_data = get_details_res.json()
    assert details_data["id"] == run_id
    assert details_data["question_text"] == "What is renewable energy forecasting accuracy?"
    assert details_data["project_name"] == "Energy AI"

    # 5. List runs for question
    list_runs_res = await client.get(f"/api/v1/questions/{q_id}/runs")
    assert list_runs_res.status_code == 200
    assert len(list_runs_res.json()) == 1


@pytest.mark.asyncio
async def test_create_run_invalid_question_id_returns_404(client: AsyncClient):
    random_uuid = str(uuid.uuid4())
    res = await client.post(f"/api/v1/questions/{random_uuid}/runs", json={})
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_delete_research_run(client: AsyncClient):
    # 1. Create project & question
    p_res = await client.post("/api/v1/projects", json={"name": "Run Delete Test", "research_topic": "Testing"})
    p_id = p_res.json()["id"]

    q_res = await client.post(f"/api/v1/projects/{p_id}/questions", json={"question": "Question for run delete test?"})
    q_id = q_res.json()["id"]

    # 2. Trigger research run
    run_res = await client.post(f"/api/v1/questions/{q_id}/runs", json={"metadata_json": {}})
    assert run_res.status_code == 201
    run_id = run_res.json()["id"]

    # 3. Delete run
    del_res = await client.delete(f"/api/v1/runs/{run_id}")
    assert del_res.status_code == 204

    # 4. Verify run is gone
    get_res = await client.get(f"/api/v1/runs/{run_id}")
    assert get_res.status_code == 404
