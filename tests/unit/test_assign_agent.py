"""
Unit tests for AssignAgent use case.
"""

import uuid
from unittest.mock import AsyncMock

import pytest

from src.application.use_cases.clients.assign_agent import AssignAgent
from src.domain.entities.client import Client
from src.domain.entities.user import User
from src.domain.exceptions import ClientNotFoundError, UserNotFoundError


@pytest.mark.asyncio
async def test_assign_agent_success():
    agent_id = uuid.uuid4()
    client_id = uuid.uuid4()

    user_repo = AsyncMock()
    user_repo.get_by_id.return_value = User(
        id=agent_id, email="agent@crm.com", full_name="Agent", role="soporte"
    )

    client_repo = AsyncMock()
    client_repo.get_by_id.return_value = Client(
        id=client_id, full_name="Client", email="cl@example.com"
    )
    client_repo.assign_agent.return_value = Client(
        id=client_id, full_name="Client", email="cl@example.com",
        assigned_agent_id=agent_id,
    )

    use_case = AssignAgent(client_repository=client_repo, user_repository=user_repo)
    result = await use_case.execute(client_id, agent_id)

    assert result.assigned_agent_id == agent_id
    client_repo.assign_agent.assert_called_once_with(client_id, agent_id)


@pytest.mark.asyncio
async def test_assign_agent_agent_not_found():
    user_repo = AsyncMock()
    user_repo.get_by_id.return_value = None

    client_repo = AsyncMock()

    use_case = AssignAgent(client_repository=client_repo, user_repository=user_repo)

    with pytest.raises(UserNotFoundError):
        await use_case.execute(uuid.uuid4(), uuid.uuid4())


@pytest.mark.asyncio
async def test_assign_agent_client_not_found():
    agent_id = uuid.uuid4()
    user_repo = AsyncMock()
    user_repo.get_by_id.return_value = User(
        id=agent_id, email="agent@crm.com", full_name="Agent", role="soporte"
    )

    client_repo = AsyncMock()
    client_repo.get_by_id.return_value = None

    use_case = AssignAgent(client_repository=client_repo, user_repository=user_repo)

    with pytest.raises(ClientNotFoundError):
        await use_case.execute(uuid.uuid4(), agent_id)
