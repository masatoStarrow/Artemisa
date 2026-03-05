"""
Use case: Get a client by ID.
"""

from uuid import UUID

from src.domain.entities.client import Client
from src.domain.exceptions import ClientNotFoundError
from src.domain.ports.client_repository import ClientRepository


class GetClient:
    def __init__(self, client_repository: ClientRepository) -> None:
        self._repo = client_repository

    async def execute(self, client_id: UUID) -> Client:
        client = await self._repo.get_by_id(client_id)
        if client is None:
            raise ClientNotFoundError()
        return client
