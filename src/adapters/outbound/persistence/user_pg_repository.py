"""
PostgreSQL implementation of UserRepository using SQLAlchemy async.
"""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.user import User
from src.domain.ports.user_repository import UserRepository
from src.adapters.outbound.persistence.models.user_model import UserModel


class UserPgRepository(UserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_entity(self, model: UserModel) -> User:
        return User(
            id=model.id,
            email=model.email,
            full_name=model.full_name,
            role=model.role,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def get_by_id(self, user_id: UUID) -> User | None:
        result = await self._session.get(UserModel, user_id)
        return self._to_entity(result) if result else None

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(UserModel).where(UserModel.email == email.lower())
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_users(
        self,
        *,
        role: str | None = None,
        is_active: bool | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[User], int]:
        stmt = select(UserModel)
        count_stmt = select(func.count()).select_from(UserModel)

        if role is not None:
            stmt = stmt.where(UserModel.role == role)
            count_stmt = count_stmt.where(UserModel.role == role)
        if is_active is not None:
            stmt = stmt.where(UserModel.is_active == is_active)
            count_stmt = count_stmt.where(UserModel.is_active == is_active)

        # Count total
        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar() or 0

        # Paginate
        offset = (page - 1) * page_size
        stmt = stmt.order_by(UserModel.created_at.desc()).offset(offset).limit(page_size)
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._to_entity(m) for m in models], total

    async def create(self, user: User) -> User:
        model = UserModel(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def update(self, user: User) -> User:
        model = await self._session.get(UserModel, user.id)
        if model is None:
            raise ValueError(f"User {user.id} not found")

        model.full_name = user.full_name
        model.role = user.role
        model.is_active = user.is_active
        model.updated_at = datetime.now(timezone.utc)

        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def deactivate(self, user_id: UUID) -> User:
        model = await self._session.get(UserModel, user_id)
        if model is None:
            raise ValueError(f"User {user_id} not found")

        model.is_active = False
        model.updated_at = datetime.now(timezone.utc)

        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)
