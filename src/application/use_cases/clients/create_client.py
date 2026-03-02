"""
Use case: Create a new client.
"""

import uuid

from src.application.dtos.client_dto import CreateClientDTO
from src.domain.entities.client import Client
from src.domain.exceptions import EmailAlreadyExistsError
from src.domain.repositories.client_repository import ClientRepository


class CreateClient:
    def __init__(self, client_repository: ClientRepository) -> None:
        self._repo = client_repository

    async def execute(self, dto: CreateClientDTO) -> Client:
        existing = await self._repo.get_by_email(dto.email)
        if existing is not None:
            raise EmailAlreadyExistsError("Ya existe un cliente con ese email")

        client = Client(
            id=uuid.uuid4(),
            company=dto.company.strip(),
            email=dto.email.strip().lower(),
            phone=dto.phone,
            status=dto.status,
        )
        return await self._repo.create(client)
