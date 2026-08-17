import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_and_list_questions(client: AsyncClient):
    # 1. Create project
    proj_res = await client.post(
        "/api/v1/projects",
        json={"name": "Manufacturing AI", "research_topic": "Robotics", "industry": "Automotive"},
    )
    project_id = proj_res.json()["id"]

    # 2. Add question to project
    q_payload = {"question": "What computer vision models improve assembly line defect detection?", "status": "active"}
    q_res = await client.post(f"/api/v1/projects/{project_id}/questions", json=q_payload)
    assert q_res.status_code == 201
    q_data = q_res.json()
    assert q_data["project_id"] == project_id
    assert q_data["question"] == q_payload["question"]

    # 3. List questions for project
    list_res = await client.get(f"/api/v1/projects/{project_id}/questions")
    assert list_res.status_code == 200
    questions = list_res.json()
    assert len(questions) == 1
    assert questions[0]["id"] == q_data["id"]


@pytest.mark.asyncio
async def test_create_question_invalid_project_id_returns_404(client: AsyncClient):
    random_uuid = str(uuid.uuid4())
    q_payload = {"question": "How does LLM agent scheduling work?"}
    res = await client.post(f"/api/v1/projects/{random_uuid}/questions", json=q_payload)
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_update_and_delete_question(client: AsyncClient):
    # 1. Create project
    proj_res = await client.post(
        "/api/v1/projects",
        json={"name": "Energy Grid AI", "research_topic": "Smart Grids", "industry": "Energy"},
    )
    project_id = proj_res.json()["id"]

    # 2. Add question
    q_payload = {"question": "Original question about battery storage?", "status": "active"}
    q_res = await client.post(f"/api/v1/projects/{project_id}/questions", json=q_payload)
    assert q_res.status_code == 201
    question_id = q_res.json()["id"]

    # 3. Get question
    get_res = await client.get(f"/api/v1/questions/{question_id}")
    assert get_res.status_code == 200
    assert get_res.json()["question"] == q_payload["question"]

    # 4. Update question
    update_res = await client.put(
        f"/api/v1/questions/{question_id}",
        json={"question": "Updated question about long-duration battery storage?", "status": "active"},
    )
    assert update_res.status_code == 200
    assert update_res.json()["question"] == "Updated question about long-duration battery storage?"

    # 5. Delete question
    del_res = await client.delete(f"/api/v1/questions/{question_id}")
    assert del_res.status_code == 204

    # 6. Verify deleted
    verify_res = await client.get(f"/api/v1/questions/{question_id}")
    assert verify_res.status_code == 404
