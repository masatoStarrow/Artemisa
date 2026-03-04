"""
Integration tests: CRUD completo de usuarios via HTTP endpoints.
"""

import uuid

import pytest
from httpx import AsyncClient

from tests.conftest import INTERNAL_HEADERS_ADMIN, INTERNAL_HEADERS_SOPORTE, ADMIN_ID


@pytest.mark.asyncio
async def test_create_user_success(client: AsyncClient, seed_users):
    response = await client.post(
        "/api/v1/users/",
        json={
            "email": "nuevo@crm.com",
            "full_name": "Nuevo Usuario",
            "role": "soporte",
        },
        headers=INTERNAL_HEADERS_ADMIN,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["data"]["email"] == "nuevo@crm.com"
    assert body["data"]["role"] == "soporte"
    assert body["data"]["is_active"] is True


@pytest.mark.asyncio
async def test_create_user_duplicate_email(client: AsyncClient, seed_users):
    response = await client.post(
        "/api/v1/users/",
        json={
            "email": "admin@crm.com",
            "full_name": "Duplicado",
            "role": "admin",
        },
        headers=INTERNAL_HEADERS_ADMIN,
    )
    assert response.status_code == 409
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "EMAIL_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_list_users_with_role_filter(client: AsyncClient, seed_users):
    response = await client.get(
        "/api/v1/users/?role=soporte",
        headers=INTERNAL_HEADERS_ADMIN,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    items = body["data"]["items"]
    assert all(u["role"] == "soporte" for u in items)


@pytest.mark.asyncio
async def test_list_users_pagination(client: AsyncClient, seed_users):
    response = await client.get(
        "/api/v1/users/?page=1&page_size=2",
        headers=INTERNAL_HEADERS_ADMIN,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["page"] == 1
    assert body["data"]["page_size"] == 2
    assert len(body["data"]["items"]) <= 2


@pytest.mark.asyncio
async def test_get_user_by_id(client: AsyncClient, seed_users):
    response = await client.get(
        f"/api/v1/users/{ADMIN_ID}",
        headers=INTERNAL_HEADERS_ADMIN,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["email"] == "admin@crm.com"


@pytest.mark.asyncio
async def test_get_user_not_found(client: AsyncClient, seed_users):
    fake_id = uuid.uuid4()
    response = await client.get(
        f"/api/v1/users/{fake_id}",
        headers=INTERNAL_HEADERS_ADMIN,
    )
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "USER_NOT_FOUND"


@pytest.mark.asyncio
async def test_update_user_role(client: AsyncClient, seed_users):
    response = await client.put(
        f"/api/v1/users/{ADMIN_ID}",
        json={"role": "soporte"},
        headers=INTERNAL_HEADERS_ADMIN,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["role"] == "soporte"


@pytest.mark.asyncio
async def test_deactivate_user(client: AsyncClient, seed_users):
    response = await client.delete(
        f"/api/v1/users/{ADMIN_ID}",
        headers=INTERNAL_HEADERS_ADMIN,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["is_active"] is False


@pytest.mark.asyncio
async def test_missing_headers_returns_422(client: AsyncClient):
    response = await client.get("/api/v1/users/")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_soporte_only_sees_active_users(client: AsyncClient, seed_users):
    """Soporte filter: should only see active users."""
    # First deactivate a user via admin
    await client.delete(
        f"/api/v1/users/{ADMIN_ID}",
        headers=INTERNAL_HEADERS_ADMIN,
    )

    # Now soporte lists users
    response = await client.get(
        "/api/v1/users/",
        headers=INTERNAL_HEADERS_SOPORTE,
    )
    assert response.status_code == 200
    body = response.json()
    for user in body["data"]["items"]:
        assert user["is_active"] is True
