"""
Use case: Update an existing client.
"""

from uuid import UUID

from src.application.dtos.client_dto import UpdateClientDTO
from src.domain.entities.client import Client
from src.domain.exceptions import ClientNotFoundError, EmailAlreadyExistsError
from src.domain.ports.client_repository import ClientRepository


class UpdateClient:
    def __init__(self, client_repository: ClientRepository) -> None:
        self._repo = client_repository

    async def execute(self, client_id: UUID, dto: UpdateClientDTO) -> Client:
        client = await self._repo.get_by_id(client_id)
        if client is None:
            raise ClientNotFoundError()

        if dto.email is not None:
            existing = await self._repo.get_by_email(dto.email)
            if existing is not None and existing.id != client_id:
                raise EmailAlreadyExistsError("Ya existe un cliente con ese email")
            client.email = dto.email.strip().lower()

        if dto.company is not None:
            client.company = dto.company.strip()
        if dto.phone is not None:
            client.phone = dto.phone
        if dto.status is not None:
            client.status = dto.status

        return await self._repo.update(client)
