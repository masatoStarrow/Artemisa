"""
FastAPI router for /api/v1/users endpoints.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.inbound.http.dependencies import UserContext, get_current_user_context
from src.adapters.inbound.http.schemas.user_schema import (
    CreateUserRequest,
    UpdateUserRequest,
    UserResponse,
)
from src.adapters.inbound.http.response_helpers import (
    success_response,
    paginated_response,
    error_response,
)
from src.application.dtos.user_dto import CreateUserDTO, UpdateUserDTO
from src.application.use_cases.users.create_user import CreateUser
from src.application.use_cases.users.deactivate_user import DeactivateUser
from src.application.use_cases.users.get_user import GetUser
from src.application.use_cases.users.list_users import ListUsers
from src.application.use_cases.users.update_user import UpdateUser
from src.domain.exceptions import EmailAlreadyExistsError, UserNotFoundError
from src.domain.value_objects.user_role import UserRole
from src.infrastructure.database.connection import get_db
from src.infrastructure.di.container import (
    get_create_user_use_case,
    get_deactivate_user_use_case,
    get_get_user_use_case,
    get_list_users_use_case,
    get_update_user_use_case,
)

router = APIRouter(prefix="/api/v1/users", tags=["Users"])


@router.get(
    "/",
    summary="Listar usuarios",
    description="Lista usuarios con filtros opcionales de rol y estado. Paginación con page y page_size.",
    responses={403: {"description": "Forbidden"}, 422: {"description": "Validation Error"}},
)
async def list_users(
    context: UserContext = Depends(get_current_user_context),
    role: str | None = Query(None, description="Filtrar por rol"),
    is_active: bool | None = Query(None, description="Filtrar por estado activo"),
    page: int = Query(1, ge=1, description="Página"),
    page_size: int = Query(10, ge=1, le=100, description="Elementos por página"),
    db: AsyncSession = Depends(get_db),
):
    # Soporte solo ve usuarios activos
    if context.role == UserRole.SOPORTE:
        is_active = True

    use_case = get_list_users_use_case(db)
    users, total = await use_case.execute(
        role=role, is_active=is_active, page=page, page_size=page_size
    )
    items = [UserResponse.model_validate(u.__dict__).model_dump(mode="json") for u in users]
    return paginated_response(items=items, total=total, page=page, page_size=page_size)


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="Crear usuario",
    description="Crea un nuevo usuario en el sistema. Acepta un campo 'id' (UUID) opcional: si se proporciona — típicamente por el API Gateway en el flujo dual-write — se usa ese UUID; si se omite, se genera uno automáticamente.",
    responses={409: {"description": "Email ya existe"}, 422: {"description": "Validation Error"}},
)
async def create_user(
    body: CreateUserRequest,
    context: UserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db),
):
    dto = CreateUserDTO(email=body.email, full_name=body.full_name, role=body.role.value, id=body.id)
    use_case = get_create_user_use_case(db)

    try:
        user = await use_case.execute(dto)
    except EmailAlreadyExistsError as e:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=error_response(e.code, e.message),
        )

    data = UserResponse.model_validate(user.__dict__).model_dump(mode="json")
    return success_response(data)


@router.get(
    "/{user_id}",
    summary="Obtener usuario por ID",
    description="Retorna un usuario específico por su UUID.",
    responses={404: {"description": "User not found"}},
)
async def get_user(
    user_id: UUID,
    context: UserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db),
):
    use_case = get_get_user_use_case(db)

    try:
        user = await use_case.execute(user_id)
    except UserNotFoundError as e:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=error_response(e.code, e.message),
        )

    data = UserResponse.model_validate(user.__dict__).model_dump(mode="json")
    return success_response(data)


@router.put(
    "/{user_id}",
    summary="Actualizar usuario",
    description="Actualiza nombre, rol o estado de un usuario.",
    responses={404: {"description": "User not found"}, 422: {"description": "Validation Error"}},
)
async def update_user(
    user_id: UUID,
    body: UpdateUserRequest,
    context: UserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db),
):
    dto = UpdateUserDTO(
        full_name=body.full_name,
        role=body.role.value if body.role else None,
        is_active=body.is_active,
    )
    use_case = get_update_user_use_case(db)

    try:
        user = await use_case.execute(user_id, dto)
    except UserNotFoundError as e:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=error_response(e.code, e.message),
        )

    data = UserResponse.model_validate(user.__dict__).model_dump(mode="json")
    return success_response(data)


@router.delete(
    "/{user_id}",
    summary="Desactivar usuario",
    description="Soft delete: pone is_active=False.",
    responses={404: {"description": "User not found"}},
)
async def deactivate_user(
    user_id: UUID,
    context: UserContext = Depends(get_current_user_context),
    db: AsyncSession = Depends(get_db),
):
    use_case = get_deactivate_user_use_case(db)

    try:
        user = await use_case.execute(user_id)
    except UserNotFoundError as e:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=error_response(e.code, e.message),
        )

    data = UserResponse.model_validate(user.__dict__).model_dump(mode="json")
    return success_response(data)
