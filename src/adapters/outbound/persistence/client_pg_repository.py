"""
PostgreSQL implementation of ClientRepository using SQLAlchemy async.
"""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.client import Client
from src.domain.repositories.client_repository import ClientRepository
from src.adapters.outbound.persistence.models.client_model import ClientModel


class ClientPgRepository(ClientRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_entity(self, model: ClientModel) -> Client:
        return Client(
            id=model.id,
            full_name=model.full_name,
            email=model.email,
            phone=model.phone,
            company=model.company,
            status=model.status,
            assigned_agent_id=model.assigned_agent_id,
            notes=model.notes,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def get_by_id(self, client_id: UUID) -> Client | None:
        result = await self._session.get(ClientModel, client_id)
        return self._to_entity(result) if result else None

    async def get_by_email(self, email: str) -> Client | None:
        stmt = select(ClientModel).where(ClientModel.email == email.lower())
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_clients(
        self,
        *,
        status: str | None = None,
        assigned_agent_id: UUID | None = None,
        company: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[Client], int]:
        stmt = select(ClientModel)
        count_stmt = select(func.count()).select_from(ClientModel)

        if status is not None:
            stmt = stmt.where(ClientModel.status == status)
            count_stmt = count_stmt.where(ClientModel.status == status)
        if assigned_agent_id is not None:
            stmt = stmt.where(ClientModel.assigned_agent_id == assigned_agent_id)
            count_stmt = count_stmt.where(ClientModel.assigned_agent_id == assigned_agent_id)
        if company is not None:
            stmt = stmt.where(ClientModel.company.ilike(f"%{company}%"))
            count_stmt = count_stmt.where(ClientModel.company.ilike(f"%{company}%"))

        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar() or 0

        offset = (page - 1) * page_size
        stmt = stmt.order_by(ClientModel.created_at.desc()).offset(offset).limit(page_size)
        result = await self._session.execute(stmt)
        models = result.scalars().all()

        return [self._to_entity(m) for m in models], total

    async def list_by_agent(
        self,
        agent_id: UUID,
        *,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[Client], int]:
        return await self.list_clients(
            assigned_agent_id=agent_id, page=page, page_size=page_size
        )

    async def create(self, client: Client) -> Client:
        model = ClientModel(
            id=client.id,
            full_name=client.full_name,
            email=client.email,
            phone=client.phone,
            company=client.company,
            status=client.status,
            assigned_agent_id=client.assigned_agent_id,
            notes=client.notes,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def update(self, client: Client) -> Client:
        model = await self._session.get(ClientModel, client.id)
        if model is None:
            raise ValueError(f"Client {client.id} not found")

        model.full_name = client.full_name
        model.email = client.email
        model.phone = client.phone
        model.company = client.company
        model.status = client.status
        model.notes = client.notes
        model.updated_at = datetime.now(timezone.utc)

        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def assign_agent(self, client_id: UUID, agent_id: UUID) -> Client:
        model = await self._session.get(ClientModel, client_id)
        if model is None:
            raise ValueError(f"Client {client_id} not found")

        model.assigned_agent_id = agent_id
        model.updated_at = datetime.now(timezone.utc)

        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def soft_delete(self, client_id: UUID) -> Client:
        model = await self._session.get(ClientModel, client_id)
        if model is None:
            raise ValueError(f"Client {client_id} not found")

        model.status = "inactivo"
        model.updated_at = datetime.now(timezone.utc)

        await self._session.flush()
        await self._session.refresh(model)
        return self._to_entity(model)
