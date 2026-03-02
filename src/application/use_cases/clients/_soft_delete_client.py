"""
Use case: Soft delete a client (set status=inactivo).
"""

from uuid import UUID

from src.domain.entities.client import Client
from src.domain.exceptions import ClientNotFoundError
from src.domain.repositories.client_repository import ClientRepository


class SoftDeleteClient:
    def __init__(self, client_repository: ClientRepository) -> None:
        self._repo = client_repository

    async def execute(self, client_id: UUID) -> Client:
        client = await self._repo.get_by_id(client_id)
        if client is None:
            raise ClientNotFoundError()
        return await self._repo.soft_delete(client_id)
