"""
Unit tests for client use cases: CreateClient, UpdateClient, SoftDeleteClient.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from src.application.dtos.client_dto import CreateClientDTO, UpdateClientDTO
from src.application.use_cases.clients.create_client import CreateClient
from src.application.use_cases.clients.update_client import UpdateClient
from src.application.use_cases.clients._soft_delete_client import SoftDeleteClient
from src.domain.entities.client import Client
from src.domain.exceptions import ClientNotFoundError, EmailAlreadyExistsError


def _make_client(**kwargs) -> Client:
    now = datetime.now(timezone.utc)
    defaults = {
        "id": uuid.uuid4(),
        "company": "Empresa Test S.A.",
        "email": "test@empresa.com",
        "phone": None,
        "status": "activo",
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(kwargs)
    return Client(**defaults)


# ── CreateClient ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_client_success():
    repo = AsyncMock()
    repo.get_by_email.return_value = None
    created = _make_client(company="Acme Corp", email="acme@corp.com")
    repo.create.return_value = created

    use_case = CreateClient(client_repository=repo)
    result = await use_case.execute(
        CreateClientDTO(company="Acme Corp", email="acme@corp.com")
    )

    repo.get_by_email.assert_called_once_with("acme@corp.com")
    repo.create.assert_called_once()
    assert result.company == "Acme Corp"
    assert result.email == "acme@corp.com"
    assert result.status == "activo"


@pytest.mark.asyncio
async def test_create_client_email_normalised():
    """Email should be lowercased and stripped."""
    repo = AsyncMock()
    repo.get_by_email.return_value = None
    repo.create.side_effect = lambda c: c

    use_case = CreateClient(client_repository=repo)
    await use_case.execute(
        CreateClientDTO(company="Test Co", email="  TEST@Example.COM  ")
    )

    client_arg = repo.create.call_args[0][0]
    assert client_arg.email == "test@example.com"


@pytest.mark.asyncio
async def test_create_client_duplicate_email_raises():
    repo = AsyncMock()
    repo.get_by_email.return_value = _make_client(email="dup@co.com")

    use_case = CreateClient(client_repository=repo)
    with pytest.raises(EmailAlreadyExistsError):
        await use_case.execute(CreateClientDTO(company="X", email="dup@co.com"))

    repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_create_client_assigns_uuid():
    repo = AsyncMock()
    repo.get_by_email.return_value = None
    repo.create.side_effect = lambda c: c

    use_case = CreateClient(client_repository=repo)
    await use_case.execute(CreateClientDTO(company="Co", email="a@b.com"))

    client_arg = repo.create.call_args[0][0]
    assert client_arg.id is not None


# ── UpdateClient ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_client_company():
    existing = _make_client(company="Old Co", email="old@co.com")
    repo = AsyncMock()
    repo.get_by_id.return_value = existing
    repo.get_by_email.return_value = None
    repo.update.side_effect = lambda c: c

    use_case = UpdateClient(client_repository=repo)
    result = await use_case.execute(
        existing.id, UpdateClientDTO(company="New Co")
    )

    assert result.company == "New Co"


@pytest.mark.asyncio
async def test_update_client_not_found_raises():
    repo = AsyncMock()
    repo.get_by_id.return_value = None

    use_case = UpdateClient(client_repository=repo)
    with pytest.raises(ClientNotFoundError):
        await use_case.execute(uuid.uuid4(), UpdateClientDTO(company="X"))


@pytest.mark.asyncio
async def test_update_client_duplicate_email_raises():
    existing = _make_client(email="owner@co.com")
    other = _make_client(email="taken@co.com")
    repo = AsyncMock()
    repo.get_by_id.return_value = existing
    repo.get_by_email.return_value = other

    use_case = UpdateClient(client_repository=repo)
    with pytest.raises(EmailAlreadyExistsError):
        await use_case.execute(
            existing.id, UpdateClientDTO(email="taken@co.com")
        )


@pytest.mark.asyncio
async def test_update_client_same_email_allowed():
    """Updating to own email (same record) should not raise."""
    existing = _make_client(email="same@co.com")
    repo = AsyncMock()
    repo.get_by_id.return_value = existing
    repo.get_by_email.return_value = existing  # same record
    repo.update.side_effect = lambda c: c

    use_case = UpdateClient(client_repository=repo)
    result = await use_case.execute(
        existing.id, UpdateClientDTO(email="same@co.com")
    )
    assert result.email == "same@co.com"


# ── SoftDeleteClient ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_soft_delete_sets_inactivo():
    existing = _make_client(status="activo")
    inactivo = _make_client(id=existing.id, status="inactivo")
    repo = AsyncMock()
    repo.get_by_id.return_value = existing
    repo.soft_delete.return_value = inactivo

    use_case = SoftDeleteClient(client_repository=repo)
    result = await use_case.execute(existing.id)

    repo.soft_delete.assert_called_once_with(existing.id)
    assert result.status == "inactivo"


@pytest.mark.asyncio
async def test_soft_delete_not_found_raises():
    repo = AsyncMock()
    repo.get_by_id.return_value = None

    use_case = SoftDeleteClient(client_repository=repo)
    with pytest.raises(ClientNotFoundError):
        await use_case.execute(uuid.uuid4())
