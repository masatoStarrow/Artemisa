"""
Integration tests: CRUD completo de clientes via HTTP endpoints.
Modelo: id, company, email, phone, status (active/inactive), created_at, updated_at.
"""

import uuid

import pytest
from httpx import AsyncClient

from tests.conftest import (
    INTERNAL_HEADERS_ADMIN,
    INTERNAL_HEADERS_SOPORTE,
    INTERNAL_HEADERS_COMERCIAL,
)

# ── Helper ────────────────────────────────────────────────────────────────────

def _client_payload(**overrides) -> dict:
    base = {
        "company": "Empresa Demo S.A.",
        "email": f"demo-{uuid.uuid4().hex[:8]}@empresa.com",
        "phone": "+573001234567",
        "status": "active",
    }
    base.update(overrides)
    return base


# ── POST /api/v1/clients/ ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_client_success(client: AsyncClient):
    payload = _client_payload(company="Acme Corp", email="acme@corp.com")
    response = await client.post("/api/v1/clients/", json=payload, headers=INTERNAL_HEADERS_ADMIN)

    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert data["company"] == "Acme Corp"
    assert data["email"] == "acme@corp.com"
    assert data["status"] == "active"
    assert data["phone"] == "+573001234567"
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


@pytest.mark.asyncio
async def test_create_client_minimal_fields(client: AsyncClient):
    """Solo company y email son requeridos."""
    response = await client.post(
        "/api/v1/clients/",
        json={"company": "Minimal S.A.", "email": "minimal@co.com"},
        headers=INTERNAL_HEADERS_ADMIN,
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["phone"] is None
    assert data["status"] == "active"


@pytest.mark.asyncio
async def test_create_client_default_status_active(client: AsyncClient):
    response = await client.post(
        "/api/v1/clients/",
        json={"company": "Status Co", "email": "status@co.com"},
        headers=INTERNAL_HEADERS_ADMIN,
    )
    assert response.status_code == 201
    assert response.json()["data"]["status"] == "active"


@pytest.mark.asyncio
async def test_create_client_inactive_status(client: AsyncClient):
    response = await client.post(
        "/api/v1/clients/",
        json={"company": "Inactive S.A.", "email": "inact@co.com", "status": "inactive"},
        headers=INTERNAL_HEADERS_ADMIN,
    )
    assert response.status_code == 201
    assert response.json()["data"]["status"] == "inactive"


@pytest.mark.asyncio
async def test_create_client_duplicate_email_returns_409(client: AsyncClient):
    payload = _client_payload(email="dup@empresa.com")
    await client.post("/api/v1/clients/", json=payload, headers=INTERNAL_HEADERS_ADMIN)
    response = await client.post("/api/v1/clients/", json=payload, headers=INTERNAL_HEADERS_ADMIN)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMAIL_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_create_client_missing_company_returns_422(client: AsyncClient):
    response = await client.post(
        "/api/v1/clients/",
        json={"email": "nocompany@co.com"},
        headers=INTERNAL_HEADERS_ADMIN,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_client_missing_email_returns_422(client: AsyncClient):
    response = await client.post(
        "/api/v1/clients/",
        json={"company": "No Email S.A."},
        headers=INTERNAL_HEADERS_ADMIN,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_client_invalid_email_returns_422(client: AsyncClient):
    response = await client.post(
        "/api/v1/clients/",
        json={"company": "Bad Email Co", "email": "not-an-email"},
        headers=INTERNAL_HEADERS_ADMIN,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_client_invalid_status_returns_422(client: AsyncClient):
    """prospecto is no longer a valid status."""
    response = await client.post(
        "/api/v1/clients/",
        json={"company": "Bad Status Co", "email": "bad@co.com", "status": "prospecto"},
        headers=INTERNAL_HEADERS_ADMIN,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_client_all_roles_can_create(client: AsyncClient):
    for i, headers in enumerate(
        [INTERNAL_HEADERS_ADMIN, INTERNAL_HEADERS_SOPORTE, INTERNAL_HEADERS_COMERCIAL]
    ):
        response = await client.post(
            "/api/v1/clients/",
            json={"company": f"Role Co {i}", "email": f"role{i}@co.com"},
            headers=headers,
        )
        assert response.status_code == 201


# ── GET /api/v1/clients/ ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_clients_empty(client: AsyncClient):
    response = await client.get("/api/v1/clients/", headers=INTERNAL_HEADERS_ADMIN)
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["items"] == []
    assert body["data"]["total"] == 0


@pytest.mark.asyncio
async def test_list_clients_returns_created(client: AsyncClient):
    await client.post(
        "/api/v1/clients/",
        json={"company": "Lista Co", "email": "lista@co.com"},
        headers=INTERNAL_HEADERS_ADMIN,
    )
    response = await client.get("/api/v1/clients/", headers=INTERNAL_HEADERS_ADMIN)
    assert response.status_code == 200
    items = response.json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["company"] == "Lista Co"


@pytest.mark.asyncio
async def test_list_clients_filter_by_status_active(client: AsyncClient):
    await client.post(
        "/api/v1/clients/",
        json={"company": "Active Co", "email": "activa@co.com", "status": "active"},
        headers=INTERNAL_HEADERS_ADMIN,
    )
    await client.post(
        "/api/v1/clients/",
        json={"company": "Inactive Co", "email": "inactiva@co.com", "status": "inactive"},
        headers=INTERNAL_HEADERS_ADMIN,
    )

    response = await client.get("/api/v1/clients/?status=active", headers=INTERNAL_HEADERS_ADMIN)
    assert response.status_code == 200
    items = response.json()["data"]["items"]
    assert len(items) == 1
    assert all(c["status"] == "active" for c in items)


@pytest.mark.asyncio
async def test_list_clients_filter_by_status_inactive(client: AsyncClient):
    await client.post(
        "/api/v1/clients/",
        json={"company": "A Co", "email": "a@co.com", "status": "active"},
        headers=INTERNAL_HEADERS_ADMIN,
    )
    await client.post(
        "/api/v1/clients/",
        json={"company": "I Co", "email": "i@co.com", "status": "inactive"},
        headers=INTERNAL_HEADERS_ADMIN,
    )

    response = await client.get("/api/v1/clients/?status=inactive", headers=INTERNAL_HEADERS_ADMIN)
    assert response.status_code == 200
    items = response.json()["data"]["items"]
    assert all(c["status"] == "inactive" for c in items)


@pytest.mark.asyncio
async def test_list_clients_pagination(client: AsyncClient):
    for i in range(5):
        await client.post(
            "/api/v1/clients/",
            json={"company": f"Co {i}", "email": f"pag{i}@co.com"},
            headers=INTERNAL_HEADERS_ADMIN,
        )

    response = await client.get(
        "/api/v1/clients/?page=1&page_size=2", headers=INTERNAL_HEADERS_ADMIN
    )
    assert response.status_code == 200
    d = response.json()["data"]
    assert d["total"] == 5
    assert len(d["items"]) == 2
    assert d["pages"] == 3


@pytest.mark.asyncio
async def test_list_clients_all_roles_allowed(client: AsyncClient):
    for headers in [INTERNAL_HEADERS_ADMIN, INTERNAL_HEADERS_SOPORTE, INTERNAL_HEADERS_COMERCIAL]:
        r = await client.get("/api/v1/clients/", headers=headers)
        assert r.status_code == 200


# ── GET /api/v1/clients/{id} ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_client_by_id_success(client: AsyncClient):
    create_r = await client.post(
        "/api/v1/clients/",
        json={"company": "Get Me Co", "email": "getme@co.com"},
        headers=INTERNAL_HEADERS_ADMIN,
    )
    client_id = create_r.json()["data"]["id"]

    response = await client.get(f"/api/v1/clients/{client_id}", headers=INTERNAL_HEADERS_ADMIN)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == client_id
    assert data["company"] == "Get Me Co"
    assert data["email"] == "getme@co.com"


@pytest.mark.asyncio
async def test_get_client_not_found_returns_404(client: AsyncClient):
    fake_id = uuid.uuid4()
    response = await client.get(f"/api/v1/clients/{fake_id}", headers=INTERNAL_HEADERS_ADMIN)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "CLIENT_NOT_FOUND"


@pytest.mark.asyncio
async def test_get_client_all_roles_allowed(client: AsyncClient):
    create_r = await client.post(
        "/api/v1/clients/",
        json={"company": "Role Test Co", "email": "roletest@co.com"},
        headers=INTERNAL_HEADERS_ADMIN,
    )
    client_id = create_r.json()["data"]["id"]

    for headers in [INTERNAL_HEADERS_ADMIN, INTERNAL_HEADERS_SOPORTE, INTERNAL_HEADERS_COMERCIAL]:
        r = await client.get(f"/api/v1/clients/{client_id}", headers=headers)
        assert r.status_code == 200


# ── PUT /api/v1/clients/{id} ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_client_company(client: AsyncClient):
    create_r = await client.post(
        "/api/v1/clients/",
        json={"company": "Original Co", "email": "upd@co.com"},
        headers=INTERNAL_HEADERS_ADMIN,
    )
    client_id = create_r.json()["data"]["id"]

    response = await client.put(
        f"/api/v1/clients/{client_id}",
        json={"company": "Updated Co"},
        headers=INTERNAL_HEADERS_ADMIN,
    )
    assert response.status_code == 200
    assert response.json()["data"]["company"] == "Updated Co"


@pytest.mark.asyncio
async def test_update_client_phone(client: AsyncClient):
    create_r = await client.post(
        "/api/v1/clients/",
        json={"company": "Phone Co", "email": "phone@co.com"},
        headers=INTERNAL_HEADERS_ADMIN,
    )
    client_id = create_r.json()["data"]["id"]

    response = await client.put(
        f"/api/v1/clients/{client_id}",
        json={"phone": "+573009876543"},
        headers=INTERNAL_HEADERS_ADMIN,
    )
    assert response.status_code == 200
    assert response.json()["data"]["phone"] == "+573009876543"


@pytest.mark.asyncio
async def test_update_client_status_to_inactive(client: AsyncClient):
    create_r = await client.post(
        "/api/v1/clients/",
        json={"company": "Status Co", "email": "statupd@co.com", "status": "active"},
        headers=INTERNAL_HEADERS_ADMIN,
    )
    client_id = create_r.json()["data"]["id"]

    response = await client.put(
        f"/api/v1/clients/{client_id}",
        json={"status": "inactive"},
        headers=INTERNAL_HEADERS_ADMIN,
    )
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "inactive"


@pytest.mark.asyncio
async def test_update_client_not_found_returns_404(client: AsyncClient):
    fake_id = uuid.uuid4()
    response = await client.put(
        f"/api/v1/clients/{fake_id}",
        json={"company": "Ghost Co"},
        headers=INTERNAL_HEADERS_ADMIN,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_client_duplicate_email_returns_409(client: AsyncClient):
    await client.post(
        "/api/v1/clients/",
        json={"company": "Co A", "email": "taken@co.com"},
        headers=INTERNAL_HEADERS_ADMIN,
    )
    create_r = await client.post(
        "/api/v1/clients/",
        json={"company": "Co B", "email": "owner@co.com"},
        headers=INTERNAL_HEADERS_ADMIN,
    )
    client_id = create_r.json()["data"]["id"]

    response = await client.put(
        f"/api/v1/clients/{client_id}",
        json={"email": "taken@co.com"},
        headers=INTERNAL_HEADERS_ADMIN,
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_update_client_all_roles_allowed_at_service_level(client: AsyncClient):
    """Artemisa no enforza roles — la autorizacion la hace Atenea."""
    create_r = await client.post(
        "/api/v1/clients/",
        json={"company": "Role Test Edit Co", "email": "roleedit@co.com"},
        headers=INTERNAL_HEADERS_ADMIN,
    )
    client_id = create_r.json()["data"]["id"]

    for headers in [INTERNAL_HEADERS_ADMIN, INTERNAL_HEADERS_SOPORTE, INTERNAL_HEADERS_COMERCIAL]:
        r = await client.put(
            f"/api/v1/clients/{client_id}",
            json={"company": "Updated by any role"},
            headers=headers,
        )
        assert r.status_code == 200


# ── DELETE /api/v1/clients/{id} ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_deactivate_client_sets_inactive(client: AsyncClient):
    create_r = await client.post(
        "/api/v1/clients/",
        json={"company": "To Deactivate", "email": "deact@co.com", "status": "active"},
        headers=INTERNAL_HEADERS_ADMIN,
    )
    client_id = create_r.json()["data"]["id"]

    response = await client.delete(
        f"/api/v1/clients/{client_id}", headers=INTERNAL_HEADERS_ADMIN
    )
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "inactive"


@pytest.mark.asyncio
async def test_deactivate_client_not_found_returns_404(client: AsyncClient):
    fake_id = uuid.uuid4()
    response = await client.delete(
        f"/api/v1/clients/{fake_id}", headers=INTERNAL_HEADERS_ADMIN
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_deactivate_client_all_roles_allowed_at_service_level(client: AsyncClient):
    """Artemisa no enforza roles — la autorizacion la hace Atenea."""
    for i, headers in enumerate(
        [INTERNAL_HEADERS_ADMIN, INTERNAL_HEADERS_SOPORTE, INTERNAL_HEADERS_COMERCIAL]
    ):
        create_r = await client.post(
            "/api/v1/clients/",
            json={"company": f"Del Co {i}", "email": f"del{i}@co.com"},
            headers=INTERNAL_HEADERS_ADMIN,
        )
        client_id = create_r.json()["data"]["id"]
        r = await client.delete(f"/api/v1/clients/{client_id}", headers=headers)
        assert r.status_code == 200
        assert r.json()["data"]["status"] == "inactive"


# ── Missing auth headers ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_request_without_headers_returns_422(client: AsyncClient):
    response = await client.get("/api/v1/clients/")
    assert response.status_code == 422
