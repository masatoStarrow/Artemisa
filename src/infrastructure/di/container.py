"""
Dependency injection container.
Assembles use cases with real repository implementations.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.outbound.persistence.user_pg_repository import UserPgRepository
from src.adapters.outbound.persistence.client_pg_repository import ClientPgRepository
from src.application.use_cases.users.get_user import GetUser
from src.application.use_cases.users.list_users import ListUsers
from src.application.use_cases.users.create_user import CreateUser
from src.application.use_cases.users.update_user import UpdateUser
from src.application.use_cases.users.deactivate_user import DeactivateUser
from src.application.use_cases.clients.get_client import GetClient
from src.application.use_cases.clients.list_clients import ListClients
from src.application.use_cases.clients.create_client import CreateClient
from src.application.use_cases.clients.update_client import UpdateClient
from src.application.use_cases.clients.assign_agent import AssignAgent


# ── User use case factories ──────────────────────────────────────────────

def get_get_user_use_case(db: AsyncSession) -> GetUser:
    return GetUser(user_repository=UserPgRepository(db))


def get_list_users_use_case(db: AsyncSession) -> ListUsers:
    return ListUsers(user_repository=UserPgRepository(db))


def get_create_user_use_case(db: AsyncSession) -> CreateUser:
    return CreateUser(user_repository=UserPgRepository(db))


def get_update_user_use_case(db: AsyncSession) -> UpdateUser:
    return UpdateUser(user_repository=UserPgRepository(db))


def get_deactivate_user_use_case(db: AsyncSession) -> DeactivateUser:
    return DeactivateUser(user_repository=UserPgRepository(db))


# ── Client use case factories ────────────────────────────────────────────

def get_get_client_use_case(db: AsyncSession) -> GetClient:
    return GetClient(client_repository=ClientPgRepository(db))


def get_list_clients_use_case(db: AsyncSession) -> ListClients:
    return ListClients(client_repository=ClientPgRepository(db))


def get_create_client_use_case(db: AsyncSession) -> CreateClient:
    return CreateClient(client_repository=ClientPgRepository(db))


def get_update_client_use_case(db: AsyncSession) -> UpdateClient:
    return UpdateClient(client_repository=ClientPgRepository(db))


def get_assign_agent_use_case(db: AsyncSession) -> AssignAgent:
    return AssignAgent(
        client_repository=ClientPgRepository(db),
        user_repository=UserPgRepository(db),
    )


def get_soft_delete_client_use_case(db: AsyncSession) -> GetClient:
    """Returns a use case that can soft-delete a client (reused from repo)."""
    # We use a thin wrapper since soft_delete is in the repository
    from src.application.use_cases.clients._soft_delete_client import SoftDeleteClient
    return SoftDeleteClient(client_repository=ClientPgRepository(db))
