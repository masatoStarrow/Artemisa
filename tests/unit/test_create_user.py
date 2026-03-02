"""
Unit tests for CreateUser use case.
"""

import uuid
from unittest.mock import AsyncMock

import pytest

from src.application.dtos.user_dto import CreateUserDTO
from src.application.use_cases.users.create_user import CreateUser
from src.domain.entities.user import User
from src.domain.exceptions import EmailAlreadyExistsError


@pytest.mark.asyncio
async def test_create_user_success():
    repo = AsyncMock()
    repo.get_by_email.return_value = None
    repo.create.return_value = User(
        id=uuid.uuid4(),
        email="nuevo@crm.com",
        full_name="Nuevo Usuario",
        role="admin",
        is_active=True,
    )

    use_case = CreateUser(user_repository=repo)
    result = await use_case.execute(
        CreateUserDTO(email="nuevo@crm.com", full_name="Nuevo Usuario", role="admin")
    )

    assert result.email == "nuevo@crm.com"
    assert result.role == "admin"
    repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_create_user_duplicate_email():
    repo = AsyncMock()
    repo.get_by_email.return_value = User(
        id=uuid.uuid4(),
        email="existe@crm.com",
        full_name="Existente",
        role="admin",
    )

    use_case = CreateUser(user_repository=repo)

    with pytest.raises(EmailAlreadyExistsError):
        await use_case.execute(
            CreateUserDTO(email="existe@crm.com", full_name="Otro", role="soporte")
        )

    repo.create.assert_not_called()
