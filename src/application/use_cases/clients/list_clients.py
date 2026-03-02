"""
Use case: List clients with filters and pagination.
"""

from uuid import UUID

from src.domain.entities.client import Client
from src.domain.repositories.client_repository import ClientRepository


class ListClients:
    def __init__(self, client_repository: ClientRepository) -> None:
        self._repo = client_repository

    async def execute(
        self,
        *,
        status: str | None = None,
        assigned_agent_id: UUID | None = None,
        company: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[Client], int]:
        return await self._repo.list_clients(
            status=status,
            assigned_agent_id=assigned_agent_id,
            company=company,
            page=page,
            page_size=page_size,
        )
