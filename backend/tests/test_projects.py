import uuid
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_and_get_project(client: AsyncClient):
    payload = {
        "name": "Retail Supply Chain AI",
        "description": "Evaluating AI inventory optimization.",
        "research_topic": "Retail Logistics",
        "industry": "Retail",
        "status": "draft",
    }
    # 1. Create project
    res = await client.post("/api/v1/projects", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == payload["name"]
    assert data["research_topic"] == payload["research_topic"]
    project_id = data["id"]

    # 2. Get project by ID
    res_get = await client.get(f"/api/v1/projects/{project_id}")
    assert res_get.status_code == 200
    assert res_get.json()["id"] == project_id

    # 3. List projects
    res_list = await client.get("/api/v1/projects")
    assert res_list.status_code == 200
    assert len(res_list.json()) >= 1


@pytest.mark.asyncio
async def test_get_invalid_project_id_returns_404(client: AsyncClient):
    random_uuid = str(uuid.uuid4())
    res = await client.get(f"/api/v1/projects/{random_uuid}")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_project_validation_failure(client: AsyncClient):
    # Short name validation error
    payload = {"name": "a", "research_topic": "AI"}
    res = await client.post("/api/v1/projects", json=payload)
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_update_and_delete_project(client: AsyncClient):
    payload = {
        "name": "Original Project Name",
        "description": "Original Description",
        "research_topic": "Original Topic",
        "industry": "Finance",
        "status": "draft",
    }
    create_res = await client.post("/api/v1/projects", json=payload)
    assert create_res.status_code == 201
    project_id = create_res.json()["id"]

    # Update project
    update_payload = {
        "name": "Updated Project Name",
        "research_topic": "Updated Topic",
        "status": "active",
    }
    update_res = await client.put(f"/api/v1/projects/{project_id}", json=update_payload)
    assert update_res.status_code == 200
    updated_data = update_res.json()
    assert updated_data["name"] == "Updated Project Name"
    assert updated_data["research_topic"] == "Updated Topic"
    assert updated_data["status"] == "active"

    # Delete project
    del_res = await client.delete(f"/api/v1/projects/{project_id}")
    assert del_res.status_code == 204

    # Verify it is gone
    get_res = await client.get(f"/api/v1/projects/{project_id}")
    assert get_res.status_code == 404
