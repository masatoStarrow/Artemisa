"""
FastAPI router for /api/v1/clients endpoints.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.inbound.http.dependencies import UserContext, get_current_user_context
from src.adapters.inbound.http.schemas.client_schema import (
    AssignAgentRequest,
    CreateClientRequest,
    UpdateClientRequest,
    ClientResponse,
)
from src.adapters.inbound.http.response_helpers import (
    success_response,
    paginated_response,
    error_response,
)
from src.application.dtos.client_dto import CreateClientDTO, UpdateClientDTO
from src.domain.exceptions import (
    ClientNotFoundError,
    EmailAlreadyExistsError,
    UserNotFoundError,
)
from src.domain.value_objects.user_role import UserRole
from src.infrastructure.database.connection import get_db
from src.infrastructure.di.container import (
    get_assign_agent_use_case,
    get_create_client_use_case,
    get_get_client_use_case,
    get_list_clients_use_case,
    get_update_client_use_case,
    get_soft_delete_client_use_case,
)

router = APIRouter(prefix="/api/v1/clients", tags=["Clients"])


@router.get(
    "/",
    summary="Listar clientes",
    description="Lista clientes con filtros opcionales. Comercial solo ve sus clientes asignados.",
    responses={422: {"description": "Validation Error"}},
)
async def list_clients(
    context: UserContext = Depends(get_current_user_context),
    client_status: str | None = Query(None, alias="status", description="Filtrar por status"),
    assigned_agent_id: UUID | None = Query(None, description="Filtrar por agente asignado"),
    company: str | None = Query(None, description="Buscar por empresa"),
    page: int = Query(1, ge=1, description="Página"),
    page_size: int = Query(10, ge=1, le=100, description="Elementos por página"),
    db: AsyncSession = Depends(get_db),
):
    # Comercial solo ve sus clientes asignados
    if context.role == UserRole.COMERCIAL:
        assigned_agent_id = context.user_id

    use_case = get_list_clients_use_case(db)
    clients, total = await use_case.execute(
        status=client_status,
        assigned_agent_id=assigned_agent_id,
        company=company,
        page=page,
        page_size=page_size,
    )
    items = [ClientResponse.model_validate(c.__dict__).model_dump(mode="json") for c in clients]
    return paginated_response(items=items, total=total, page=page, page_size=page_size)


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="Crear cliente",
    description="Crea un nuevo cliente del CRM.",
    responses={409: {"description": "Email ya existe"}, 422: {"description": "Validation Error"}},
)
async def create_client(
    body: CreateClientRequest,
    context: UserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db),
):
    dto = CreateClientDTO(
        full_name=body.full_name,
        email=body.email,
        phone=body.phone,
        company=body.company,
        status=body.status.value,
        assigned_agent_id=body.assigned_agent_id,
        notes=body.notes,
    )
    use_case = get_create_client_use_case(db)

    try:
        client = await use_case.execute(dto)
    except EmailAlreadyExistsError as e:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=error_response(e.code, e.message),
        )

    data = ClientResponse.model_validate(client.__dict__).model_dump(mode="json")
    return success_response(data)


@router.get(
    "/agent/{agent_id}",
    summary="Listar clientes por agente",
    description="Retorna los clientes asignados a un agente específico.",
)
async def list_clients_by_agent(
    agent_id: UUID,
    context: UserContext = Depends(get_current_user_context),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    use_case = get_list_clients_use_case(db)
    clients, total = await use_case.execute(
        assigned_agent_id=agent_id, page=page, page_size=page_size
    )
    items = [ClientResponse.model_validate(c.__dict__).model_dump(mode="json") for c in clients]
    return paginated_response(items=items, total=total, page=page, page_size=page_size)


@router.get(
    "/{client_id}",
    summary="Obtener cliente por ID",
    description="Retorna un cliente específico por su UUID.",
    responses={404: {"description": "Client not found"}},
)
async def get_client(
    client_id: UUID,
    context: UserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db),
):
    use_case = get_get_client_use_case(db)

    try:
        client = await use_case.execute(client_id)
    except ClientNotFoundError as e:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=error_response(e.code, e.message),
        )

    data = ClientResponse.model_validate(client.__dict__).model_dump(mode="json")
    return success_response(data)


@router.put(
    "/{client_id}",
    summary="Actualizar cliente",
    description="Actualiza los datos de un cliente existente.",
    responses={404: {"description": "Client not found"}, 409: {"description": "Email duplicado"}},
)
async def update_client(
    client_id: UUID,
    body: UpdateClientRequest,
    context: UserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db),
):
    dto = UpdateClientDTO(
        full_name=body.full_name,
        email=body.email,
        phone=body.phone,
        company=body.company,
        status=body.status.value if body.status else None,
        notes=body.notes,
    )
    use_case = get_update_client_use_case(db)

    try:
        client = await use_case.execute(client_id, dto)
    except ClientNotFoundError as e:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=error_response(e.code, e.message),
        )
    except EmailAlreadyExistsError as e:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=error_response(e.code, e.message),
        )

    data = ClientResponse.model_validate(client.__dict__).model_dump(mode="json")
    return success_response(data)


@router.delete(
    "/{client_id}",
    summary="Eliminar cliente (soft delete)",
    description="Cambia el status del cliente a 'inactivo'.",
    responses={404: {"description": "Client not found"}},
)
async def delete_client(
    client_id: UUID,
    context: UserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db),
):
    use_case = get_soft_delete_client_use_case(db)

    try:
        client = await use_case.execute(client_id)
    except ClientNotFoundError as e:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=error_response(e.code, e.message),
        )

    data = ClientResponse.model_validate(client.__dict__).model_dump(mode="json")
    return success_response(data)


@router.patch(
    "/{client_id}/assign",
    summary="Asignar agente a cliente",
    description="Asigna un agente (usuario) como responsable de un cliente.",
    responses={404: {"description": "Client or agent not found"}},
)
async def assign_agent(
    client_id: UUID,
    body: AssignAgentRequest,
    context: UserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db),
):
    use_case = get_assign_agent_use_case(db)

    try:
        client = await use_case.execute(client_id, body.agent_id)
    except ClientNotFoundError as e:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=error_response(e.code, e.message),
        )
    except UserNotFoundError as e:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=error_response(e.code, e.message),
        )

    data = ClientResponse.model_validate(client.__dict__).model_dump(mode="json")
    return success_response(data)
