"""
FastAPI router for /api/v1/clients endpoints.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.inbound.http.dependencies import UserContext, get_current_user_context
from src.adapters.inbound.http.schemas.client_schema import (
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
)
from src.infrastructure.database.connection import get_db
from src.infrastructure.di.container import (
    get_create_client_use_case,
    get_get_client_use_case,
    get_list_clients_use_case,
    get_update_client_use_case,
    get_soft_delete_client_use_case,
)

router = APIRouter(prefix="/api/v1/clients", tags=["Clients"])


# ── GET /api/v1/clients/ ─────────────────────────────────────────────────

@router.get(
    "/",
    summary="Listar clientes",
    description=(
        "Devuelve una lista paginada de clientes. "
        "Se puede filtrar por estado (activo / inactivo)."
    ),
    responses={422: {"description": "Validation Error"}},
)
async def list_clients(
    context: UserContext = Depends(get_current_user_context),
    client_status: str | None = Query(None, alias="status", description="Filtrar por status (activo/inactivo)"),
    page: int = Query(1, ge=1, description="Página"),
    page_size: int = Query(10, ge=1, le=100, description="Elementos por página"),
    db: AsyncSession = Depends(get_db),
):
    use_case = get_list_clients_use_case(db)
    clients, total = await use_case.execute(
        status=client_status,
        page=page,
        page_size=page_size,
    )
    items = [ClientResponse.model_validate(c.__dict__).model_dump(mode="json") for c in clients]
    return paginated_response(items=items, total=total, page=page, page_size=page_size)


# ── POST /api/v1/clients/ ────────────────────────────────────────────────

@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="Crear cliente",
    description="Crea un nuevo cliente del CRM. Campos requeridos: company, email.",
    responses={
        409: {"description": "Email ya existe"},
        422: {"description": "Validation Error"},
    },
)
async def create_client(
    body: CreateClientRequest,
    context: UserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db),
):
    dto = CreateClientDTO(
        company=body.company,
        email=body.email,
        phone=body.phone,
        status=body.status.value,
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


# ── GET /api/v1/clients/{client_id} ──────────────────────────────────────

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


# ── PUT /api/v1/clients/{client_id} ──────────────────────────────────────

@router.put(
    "/{client_id}",
    summary="Actualizar cliente",
    description="Actualiza los datos de un cliente existente.",
    responses={
        404: {"description": "Client not found"},
        409: {"description": "Email duplicado"},
    },
)
async def update_client(
    client_id: UUID,
    body: UpdateClientRequest,
    context: UserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db),
):
    dto = UpdateClientDTO(
        company=body.company,
        email=body.email,
        phone=body.phone,
        status=body.status.value if body.status else None,
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


# ── DELETE /api/v1/clients/{client_id} ────────────────────────────────────

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
