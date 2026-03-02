"""
Use case: Assign an agent to a client.
"""

from uuid import UUID

from src.domain.entities.client import Client
from src.domain.exceptions import ClientNotFoundError, UserNotFoundError
from src.domain.repositories.client_repository import ClientRepository
from src.domain.repositories.user_repository import UserRepository


class AssignAgent:
    def __init__(
        self,
        client_repository: ClientRepository,
        user_repository: UserRepository,
    ) -> None:
        self._client_repo = client_repository
        self._user_repo = user_repository

    async def execute(self, client_id: UUID, agent_id: UUID) -> Client:
        # Verify agent exists
        agent = await self._user_repo.get_by_id(agent_id)
        if agent is None:
            raise UserNotFoundError("No existe un agente con ese ID")

        # Verify client exists
        client = await self._client_repo.get_by_id(client_id)
        if client is None:
            raise ClientNotFoundError()

        return await self._client_repo.assign_agent(client_id, agent_id)
