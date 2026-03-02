"""
Integration tests: CRUD completo de clientes via HTTP endpoints.
"""

import uuid

import pytest
from httpx import AsyncClient

from tests.conftest import (
    INTERNAL_HEADERS_ADMIN,
    INTERNAL_HEADERS_SOPORTE,
    INTERNAL_HEADERS_COMERCIAL,
    ADMIN_ID,
    SOPORTE_ID,
    COMERCIAL_ID,
)


@pytest.mark.asyncio
async def test_create_client_success(client: AsyncClient, seed_users):
    response = await client.post(
        "/api/v1/clients/",
        json={
            "full_name": "Cliente Nuevo",
            "email": "cliente@empresa.com",
            "phone": "+57300123456",
            "company": "Empresa S.A.",
            "status": "prospecto",
        },
        headers=INTERNAL_HEADERS_ADMIN,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["data"]["email"] == "cliente@empresa.com"
    assert body["data"]["status"] == "prospecto"


@pytest.mark.asyncio
async def test_create_client_duplicate_email(client: AsyncClient, seed_users):
    # Create first
    await client.post(
        "/api/v1/clients/",
        json={"full_name": "C1", "email": "dup@empresa.com"},
        headers=INTERNAL_HEADERS_ADMIN,
    )
    # Duplicate
    response = await client.post(
        "/api/v1/clients/",
        json={"full_name": "C2", "email": "dup@empresa.com"},
        headers=INTERNAL_HEADERS_ADMIN,
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMAIL_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_list_clients_filter_by_status(client: AsyncClient, seed_users):
    # Create one active client
    await client.post(
        "/api/v1/clients/",
        json={"full_name": "Activo", "email": "activo@e.com", "status": "activo"},
        headers=INTERNAL_HEADERS_ADMIN,
    )
    # Create one prospecto client
    await client.post(
        "/api/v1/clients/",
        json={"full_name": "Prospecto", "email": "prosp@e.com", "status": "prospecto"},
        headers=INTERNAL_HEADERS_ADMIN,
    )

    response = await client.get(
        "/api/v1/clients/?status=activo",
        headers=INTERNAL_HEADERS_ADMIN,
    )
    assert response.status_code == 200
    items = response.json()["data"]["items"]
    assert all(c["status"] == "activo" for c in items)


@pytest.mark.asyncio
async def test_list_clients_by_agent(client: AsyncClient, seed_users):
    # Create client assigned to soporte
    await client.post(
        "/api/v1/clients/",
        json={
            "full_name": "Assigned Client",
            "email": "assigned@e.com",
            "assigned_agent_id": str(SOPORTE_ID),
        },
        headers=INTERNAL_HEADERS_ADMIN,
    )

    response = await client.get(
        f"/api/v1/clients/agent/{SOPORTE_ID}",
        headers=INTERNAL_HEADERS_ADMIN,
    )
    assert response.status_code == 200
    items = response.json()["data"]["items"]
    assert len(items) >= 1
    assert items[0]["assigned_agent_id"] == str(SOPORTE_ID)


@pytest.mark.asyncio
async def test_get_client_by_id(client: AsyncClient, seed_users):
    # Create a client
    create_resp = await client.post(
        "/api/v1/clients/",
        json={"full_name": "Get Me", "email": "getme@e.com"},
        headers=INTERNAL_HEADERS_ADMIN,
    )
    client_id = create_resp.json()["data"]["id"]

    response = await client.get(
        f"/api/v1/clients/{client_id}",
        headers=INTERNAL_HEADERS_ADMIN,
    )
    assert response.status_code == 200
    assert response.json()["data"]["full_name"] == "Get Me"


@pytest.mark.asyncio
async def test_get_client_not_found(client: AsyncClient, seed_users):
    fake_id = uuid.uuid4()
    response = await client.get(
        f"/api/v1/clients/{fake_id}",
        headers=INTERNAL_HEADERS_ADMIN,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_client(client: AsyncClient, seed_users):
    create_resp = await client.post(
        "/api/v1/clients/",
        json={"full_name": "Original", "email": "original@e.com"},
        headers=INTERNAL_HEADERS_ADMIN,
    )
    client_id = create_resp.json()["data"]["id"]

    response = await client.put(
        f"/api/v1/clients/{client_id}",
        json={"full_name": "Updated Name", "company": "New Co"},
        headers=INTERNAL_HEADERS_ADMIN,
    )
    assert response.status_code == 200
    assert response.json()["data"]["full_name"] == "Updated Name"
    assert response.json()["data"]["company"] == "New Co"


@pytest.mark.asyncio
async def test_soft_delete_client(client: AsyncClient, seed_users):
    create_resp = await client.post(
        "/api/v1/clients/",
        json={"full_name": "To Delete", "email": "delete@e.com", "status": "activo"},
        headers=INTERNAL_HEADERS_ADMIN,
    )
    client_id = create_resp.json()["data"]["id"]

    response = await client.delete(
        f"/api/v1/clients/{client_id}",
        headers=INTERNAL_HEADERS_ADMIN,
    )
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "inactivo"


@pytest.mark.asyncio
async def test_assign_agent_success(client: AsyncClient, seed_users):
    create_resp = await client.post(
        "/api/v1/clients/",
        json={"full_name": "AssignTest", "email": "assign@e.com"},
        headers=INTERNAL_HEADERS_ADMIN,
    )
    client_id = create_resp.json()["data"]["id"]

    response = await client.patch(
        f"/api/v1/clients/{client_id}/assign",
        json={"agent_id": str(SOPORTE_ID)},
        headers=INTERNAL_HEADERS_ADMIN,
    )
    assert response.status_code == 200
    assert response.json()["data"]["assigned_agent_id"] == str(SOPORTE_ID)


@pytest.mark.asyncio
async def test_assign_nonexistent_agent(client: AsyncClient, seed_users):
    create_resp = await client.post(
        "/api/v1/clients/",
        json={"full_name": "NoAgent", "email": "noagent@e.com"},
        headers=INTERNAL_HEADERS_ADMIN,
    )
    client_id = create_resp.json()["data"]["id"]

    fake_agent = uuid.uuid4()
    response = await client.patch(
        f"/api/v1/clients/{client_id}/assign",
        json={"agent_id": str(fake_agent)},
        headers=INTERNAL_HEADERS_ADMIN,
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "USER_NOT_FOUND"


@pytest.mark.asyncio
async def test_comercial_only_sees_own_clients(client: AsyncClient, seed_users):
    """Comercial should only see clients assigned to them."""
    # Create client assigned to comercial
    await client.post(
        "/api/v1/clients/",
        json={
            "full_name": "My Client",
            "email": "my@e.com",
            "assigned_agent_id": str(COMERCIAL_ID),
        },
        headers=INTERNAL_HEADERS_ADMIN,
    )
    # Create client assigned to someone else
    await client.post(
        "/api/v1/clients/",
        json={
            "full_name": "Not Mine",
            "email": "notmine@e.com",
            "assigned_agent_id": str(SOPORTE_ID),
        },
        headers=INTERNAL_HEADERS_ADMIN,
    )

    response = await client.get(
        "/api/v1/clients/",
        headers=INTERNAL_HEADERS_COMERCIAL,
    )
    assert response.status_code == 200
    items = response.json()["data"]["items"]
    # All should be assigned to comercial
    for item in items:
        assert item["assigned_agent_id"] == str(COMERCIAL_ID)
