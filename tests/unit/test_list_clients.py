"""
Unit tests for ListClients use case — filters and pagination.
"""

import uuid
from unittest.mock import AsyncMock

import pytest

from src.application.use_cases.clients.list_clients import ListClients
from src.domain.entities.client import Client


def _make_client(**kwargs) -> Client:
    defaults = {
        "id": uuid.uuid4(),
        "company": "Empresa Test S.A.",
        "email": "test@example.com",
        "phone": None,
        "status": "activo",
    }
    defaults.update(kwargs)
    return Client(**defaults)


@pytest.mark.asyncio
async def test_list_clients_no_filters():
    clients = [_make_client(company=f"Company {i}") for i in range(3)]
    repo = AsyncMock()
    repo.list_clients.return_value = (clients, 3)

    use_case = ListClients(client_repository=repo)
    items, total = await use_case.execute()

    assert total == 3
    assert len(items) == 3
    repo.list_clients.assert_called_once_with(
        status=None, page=1, page_size=10
    )


@pytest.mark.asyncio
async def test_list_clients_filter_by_status():
    repo = AsyncMock()
    repo.list_clients.return_value = ([], 0)

    use_case = ListClients(client_repository=repo)
    await use_case.execute(status="activo")

    repo.list_clients.assert_called_once_with(
        status="activo", page=1, page_size=10
    )


@pytest.mark.asyncio
async def test_list_clients_pagination():
    repo = AsyncMock()
    repo.list_clients.return_value = ([], 50)

    use_case = ListClients(client_repository=repo)
    _, total = await use_case.execute(page=3, page_size=5)

    assert total == 50
    repo.list_clients.assert_called_once_with(
        status=None, page=3, page_size=5
    )


@pytest.mark.asyncio
async def test_list_clients_filter_by_status_inactivo():
    repo = AsyncMock()
    repo.list_clients.return_value = ([], 0)

    use_case = ListClients(client_repository=repo)
    await use_case.execute(status="inactivo")

    repo.list_clients.assert_called_once_with(
        status="inactivo", page=1, page_size=10
    )


@pytest.mark.asyncio
async def test_list_clients_returns_clients():
    clients = [
        _make_client(email="a@b.com", company="Alfa S.A."),
        _make_client(email="c@d.com", company="Beta Corp"),
    ]
    repo = AsyncMock()
    repo.list_clients.return_value = (clients, 2)

    use_case = ListClients(client_repository=repo)
    items, total = await use_case.execute()

    assert total == 2
    assert items[0].company == "Alfa S.A."
    assert items[1].company == "Beta Corp"
