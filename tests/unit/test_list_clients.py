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
        "full_name": "Test Client",
        "email": "test@example.com",
        "phone": None,
        "company": None,
        "status": "activo",
        "assigned_agent_id": None,
        "notes": None,
    }
    defaults.update(kwargs)
    return Client(**defaults)


@pytest.mark.asyncio
async def test_list_clients_no_filters():
    clients = [_make_client(full_name=f"Client {i}") for i in range(3)]
    repo = AsyncMock()
    repo.list_clients.return_value = (clients, 3)

    use_case = ListClients(client_repository=repo)
    items, total = await use_case.execute()

    assert total == 3
    assert len(items) == 3
    repo.list_clients.assert_called_once_with(
        status=None, assigned_agent_id=None, company=None, page=1, page_size=10
    )


@pytest.mark.asyncio
async def test_list_clients_filter_by_status():
    repo = AsyncMock()
    repo.list_clients.return_value = ([], 0)

    use_case = ListClients(client_repository=repo)
    await use_case.execute(status="activo")

    repo.list_clients.assert_called_once_with(
        status="activo", assigned_agent_id=None, company=None, page=1, page_size=10
    )


@pytest.mark.asyncio
async def test_list_clients_pagination():
    repo = AsyncMock()
    repo.list_clients.return_value = ([], 50)

    use_case = ListClients(client_repository=repo)
    _, total = await use_case.execute(page=3, page_size=5)

    assert total == 50
    repo.list_clients.assert_called_once_with(
        status=None, assigned_agent_id=None, company=None, page=3, page_size=5
    )


@pytest.mark.asyncio
async def test_list_clients_filter_by_agent():
    agent_id = uuid.uuid4()
    repo = AsyncMock()
    repo.list_clients.return_value = ([], 0)

    use_case = ListClients(client_repository=repo)
    await use_case.execute(assigned_agent_id=agent_id)

    repo.list_clients.assert_called_once_with(
        status=None, assigned_agent_id=agent_id, company=None, page=1, page_size=10
    )
