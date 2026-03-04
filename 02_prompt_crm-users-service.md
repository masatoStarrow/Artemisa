# PROMPT — `crm-users-service`

## Contexto general del proyecto

Eres el **microservicio de usuarios** de un CRM empresarial en migración a AWS. Este servicio es responsable exclusivamente de la gestión del perfil de usuarios del sistema: crear, consultar, actualizar y desactivar cuentas. **No emite tokens JWT** — eso es responsabilidad del API Gateway. Recibe todas sus peticiones desde el Gateway, que inyecta headers internos (`X-User-Id`, `X-User-Role`, `X-Request-Id`) en lugar de tokens.

Este servicio también gestiona la **tabla de clientes del CRM** (empresas/contactos comerciales). Los clientes solo viven en este microservicio (no hay dual-write para clientes).

---

## Stack tecnológico

| Componente | Tecnología |
|---|---|
| Framework | FastAPI 0.135 |
| Lenguaje | Python 3.13 |
| ORM | SQLAlchemy 2.0 async |
| Driver PostgreSQL | asyncpg |
| Migraciones | Alembic |
| Base de datos | PostgreSQL 15 (Docker local → AWS RDS en producción) |
| Validación | Pydantic v2 + email-validator |
| Documentación | FastAPI nativo (Swagger UI + ReDoc) |
| Testing | pytest + pytest-asyncio + httpx AsyncClient |
| Containerización | Docker + docker-compose |
| Variables de entorno | pydantic-settings (BaseSettings) |

---

## Arquitectura: Hexagonal (Ports & Adapters)

```
src/
├── domain/                          # DOMINIO PURO — cero imports de frameworks
│   ├── entities/
│   │   ├── user.py                  # @dataclass User: id, email, full_name, role, is_active
│   │   └── client.py                # @dataclass Client: id, company, email, phone, status
│   ├── value_objects/
│   │   ├── email.py                 # ValueObject Email con validación
│   │   ├── user_role.py             # Enum: admin, soporte, comercial
│   │   └── client_status.py         # Enum: active, inactive
│   ├── repositories/
│   │   ├── user_repository.py       # ABC UserRepository
│   │   └── client_repository.py     # ABC ClientRepository (get_by_id, get_by_email, list, create, update, soft_delete)
│   └── exceptions.py                # UserNotFoundError, EmailAlreadyExistsError, ClientNotFoundError, ForbiddenError
│
├── application/                     # CASOS DE USO — solo conoce el dominio
│   ├── use_cases/
│   │   ├── users/
│   │   │   ├── get_user.py          # Buscar por ID
│   │   │   ├── list_users.py        # Listar con filtros y paginación
│   │   │   ├── create_user.py       # Crear usuario
│   │   │   ├── update_user.py       # Actualizar perfil
│   │   │   └── deactivate_user.py   # Soft delete (is_active=False)
│   │   └── clients/
│   │       ├── get_client.py
│   │       ├── list_clients.py      # Filtro: status. Paginación: page, page_size
│   │       ├── create_client.py     # Verifica email único → crea cliente
│   │       ├── update_client.py     # Verifica email único si cambia → actualiza
│   │       └── _soft_delete_client.py  # DELETE → status = 'inactive'
│   └── dtos/
│       ├── user_dto.py              # CreateUserDTO, UpdateUserDTO
│       └── client_dto.py            # CreateClientDTO(company, email, phone, status), UpdateClientDTO(all optional)
│
├── adapters/
│   ├── inbound/
│   │   └── http/
│   │       ├── routers/
│   │       │   ├── user_router.py   # /users endpoints (5)
│   │       │   └── client_router.py # /clients endpoints (5)
│   │       ├── schemas/
│   │       │   ├── user_schema.py   # Pydantic schemas request/response
│   │       │   └── client_schema.py # CreateClientRequest, UpdateClientRequest, ClientResponse
│   │       ├── dependencies.py      # Extrae X-User-Id, X-User-Role de headers
│   │       ├── response_helpers.py  # success_response, paginated_response, error_response
│   │       └── validators.py
│   │
│   └── outbound/
│       └── persistence/
│           ├── models/
│           │   ├── user_model.py    # SQLAlchemy ORM Model users
│           │   └── client_model.py  # SQLAlchemy ORM Model clients (company NOT NULL, status default 'active')
│           ├── user_pg_repository.py    # Implementa UserRepository ABC
│           └── client_pg_repository.py  # Implementa ClientRepository ABC
│
└── infrastructure/
    ├── database/
    │   ├── connection.py            # Engine async, SessionLocal, get_db dependency
    │   └── migrations/              # Alembic: env.py, versions/
    ├── logging/
    │   └── setup.py
    └── di/
        └── container.py             # Ensambla use_cases con repositorios reales
```

---

## Modelos de base de datos

### Tabla `users` (réplica de perfil — sin password)

```sql
CREATE TABLE users (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email        VARCHAR(255) UNIQUE NOT NULL,
    full_name    VARCHAR(255) NOT NULL,
    role         VARCHAR(20) NOT NULL CHECK (role IN ('admin','soporte','comercial')),
    is_active    BOOLEAN NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

> **Nota importante:** Este servicio guarda el perfil del usuario (nombre, rol, estado). El password hash **no vive aquí**, vive en el Gateway. Esta tabla se sincroniza cuando el Gateway crea un usuario nuevo.

### Tabla `clients`

```sql
CREATE TABLE clients (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company      VARCHAR(255) NOT NULL,
    email        VARCHAR(255) UNIQUE NOT NULL,
    phone        VARCHAR(50),
    status       VARCHAR(20) NOT NULL DEFAULT 'active'
                 CHECK (status IN ('active','inactive')),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Índices de performance
CREATE INDEX idx_clients_status ON clients(status);
```

---

## Endpoints a implementar

### Usuarios `/api/v1/users`

| Método | Ruta | Descripción | Roles permitidos |
|--------|------|-------------|-----------------|
| GET | `/api/v1/users/` | Listar usuarios. Filtros: `role`, `is_active`. Paginación: `page`, `page_size` | admin |
| POST | `/api/v1/users/` | Crear usuario nuevo | admin |
| GET | `/api/v1/users/{user_id}` | Obtener usuario por ID | admin, soporte |
| PUT | `/api/v1/users/{user_id}` | Actualizar nombre, rol, estado | admin |
| DELETE | `/api/v1/users/{user_id}` | Desactivar usuario (soft delete) | admin |

### Clientes `/api/v1/clients`

| Método | Ruta | Descripción | Roles permitidos |
|--------|------|-------------|-----------------|
| GET | `/api/v1/clients/` | Listar clientes. Filtro: `status`. Paginación: `page`, `page_size` | Todos |
| POST | `/api/v1/clients/` | Crear cliente. Campos requeridos: `company`, `email` | admin, soporte |
| GET | `/api/v1/clients/{client_id}` | Obtener cliente por ID | Todos |
| PUT | `/api/v1/clients/{client_id}` | Actualizar datos del cliente | admin, soporte |
| DELETE | `/api/v1/clients/{client_id}` | Eliminar cliente (soft delete → `status='inactive'`) | admin |

### Health

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/v1/health/` | Estado del servicio y conexión a DB |

---

## Contrato de respuestas HTTP

Mismo envelope que el Gateway:

```json
// Éxito — lista con paginación
{
  "success": true,
  "data": {
    "items": [...],
    "total": 45,
    "page": 1,
    "page_size": 10,
    "pages": 5
  }
}

// Éxito — objeto único (ejemplo: cliente)
{
  "success": true,
  "data": {
    "id": "a1b2c3d4-...",
    "company": "Acme Corporation",
    "email": "contacto@acme.com",
    "phone": "+1-555-100-2000",
    "status": "active",
    "created_at": "2025-01-15T10:30:00Z",
    "updated_at": "2025-01-15T10:30:00Z"
  }
}

// Error
{
  "success": false,
  "error": {
    "code": "CLIENT_NOT_FOUND",
    "message": "No existe un cliente con ese ID"
  }
}
```

Códigos de error de dominio:
- `USER_NOT_FOUND` → 404
- `CLIENT_NOT_FOUND` → 404
- `EMAIL_ALREADY_EXISTS` → 409
- `VALIDATION_ERROR` → 422
- `FORBIDDEN` → 403

---

## Headers internos (desde el Gateway)

Este servicio **no valida JWT**. Confía en los headers que inyecta el Gateway:

```python
# src/adapters/inbound/http/dependencies.py

async def get_current_user_context(
    x_user_id: str = Header(...),
    x_user_role: str = Header(...),
    x_request_id: str = Header(...)
) -> UserContext:
    return UserContext(
        user_id=UUID(x_user_id),
        role=UserRole(x_user_role),
        request_id=x_request_id
    )
```

---

## Configuración

### `.env.example`

```env
# Base de datos
DB_NAME=crm_users_db
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=db
DB_PORT=5432
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20

# App
APP_ENV=local
APP_PORT=8001
LOG_LEVEL=INFO
```

### `config/settings.py` (Pydantic BaseSettings)

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    db_name: str
    db_user: str
    db_password: str
    db_host: str
    db_port: int = 5432
    db_pool_size: int = 10
    db_max_overflow: int = 20
    app_env: str = "local"
    app_port: int = 8001
    log_level: str = "INFO"

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    class Config:
        env_file = ".env"
```

---

## Conexión a base de datos (mejores prácticas)

```python
# src/infrastructure/database/connection.py

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

engine = create_async_engine(
    settings.database_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_pre_ping=True,          # Verifica conexión antes de usar (crucial para RDS)
    pool_recycle=3600,           # Recicla conexiones cada hora (evita timeouts RDS)
    echo=settings.app_env == "local",
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

class Base(DeclarativeBase):
    pass

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

---

## Docker

### `Dockerfile`

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8001
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "4"]
```

### `docker-compose.yml`

```yaml
version: "3.9"
services:
  users-service:
    build: .
    ports:
      - "8001:8001"
    env_file: .env
    depends_on:
      db:
        condition: service_healthy

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: crm_users_db
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5433:5432"
    volumes:
      - users_postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  users_postgres_data:
```

---

## Documentación (Swagger)

FastAPI genera Swagger automáticamente. Configurar en `main.py`:

```python
app = FastAPI(
    title="CRM Users Service",
    description="Gestión de usuarios del sistema y clientes del CRM.",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)
```

Cada router y endpoint debe incluir:
- `tags` para agrupación
- `summary` y `description` en cada operación
- `response_model` con el schema correcto
- `responses` documentando 400, 403, 404, 409, 422

---

## Testing

### Estructura

```
tests/
├── conftest.py                       # engine de test, sesión DB, fixtures de usuarios y clientes
├── unit/
│   ├── test_assign_agent.py          # 10 tests — Create/Update/SoftDelete use cases (mocks)
│   └── test_list_clients.py          # 5 tests — ListClients use case (filtros y paginación)
└── integration/
    ├── test_user_endpoints.py        # 11 tests — CRUD completo de usuarios
    └── test_client_endpoints.py      # 30 tests — CRUD completo de clientes, validaciones, paginación
```

### Casos de prueba obligatorios

**Usuarios:**
- ✅ Crear usuario con datos válidos → 201
- ❌ Crear usuario con email duplicado → 409
- ✅ Listar usuarios con filtro `role=soporte` → retorna solo soporte
- ✅ Listar con paginación `page=2&page_size=5`
- ✅ Obtener usuario por ID existente → 200
- ❌ Obtener usuario con ID inexistente → 404
- ✅ Actualizar rol de usuario → 200
- ✅ Desactivar usuario → `is_active=False`
- ❌ Acceso sin headers internos → 422

**Clientes:**
- ✅ Crear cliente con datos válidos (company + email) → 201
- ❌ Crear cliente con email duplicado → 409
- ❌ Crear cliente sin company → 422
- ❌ Crear cliente sin email → 422
- ❌ Crear cliente con email inválido → 422
- ❌ Crear cliente con company vacía (< 2 chars) → 422
- ❌ Crear cliente con status inválido → 422
- ✅ Listar clientes filtrados por `status=active`
- ✅ Listar con paginación `page=1&page_size=5`
- ✅ Obtener cliente por ID → 200
- ❌ Obtener cliente con ID inexistente → 404
- ✅ Actualizar company de cliente → 200
- ✅ Actualizar email de cliente → 200
- ❌ Actualizar con email duplicado → 409
- ✅ Soft delete → `status='inactive'`
- ❌ Soft delete con ID inexistente → 404

---

## Uso del rol en los microservicios

**Este servicio no autoriza — eso ya lo hizo el Gateway.** Si una request llega aquí, el acceso ya fue validado. El rol (`X-User-Role`) se usa únicamente para **filtrar qué datos retorna cada endpoint**.

```python
# src/adapters/inbound/http/routers/user_router.py

@router.get("/")
async def list_users(
    context: UserContext = Depends(get_current_user_context),
    use_case: ListUsers  = Depends(get_list_users_use_case),
):
    if context.role == UserRole.SOPORTE:
        # Soporte solo ve usuarios activos
        return await use_case.execute(filters={"is_active": True})
    # Admin ve todo
    return await use_case.execute()
```

> **Regla:** autorización → Gateway. Filtrado de datos → microservicio.
---

## Paso a paso de implementación

1. **Setup inicial**
   - `pip install fastapi uvicorn sqlalchemy asyncpg alembic pydantic-settings email-validator pytest pytest-asyncio httpx`
   - Crear estructura de carpetas
   - Configurar `config/settings.py` con BaseSettings

2. **Dominio**
   - Crear dataclasses `User` y `Client` (Python puro)
   - Crear value objects: `Email`, `UserRole`, `ClientStatus`
   - Definir ABCs de repositorios
   - Definir excepciones de dominio

3. **Base de datos**
   - Configurar `connection.py` con engine async y pool
   - Crear modelos SQLAlchemy `UserModel` y `ClientModel`
   - Inicializar Alembic: `alembic init migrations`
   - Configurar `migrations/env.py` para async
   - Generar primera migración: `alembic revision --autogenerate -m "initial"`

4. **Casos de uso + DTOs**
   - Implementar todos los casos de uso de users y clients
   - Crear DTOs de entrada y salida

5. **Adaptadores outbound**
   - Implementar `UserPgRepository` y `ClientPgRepository`

6. **Adaptadores inbound**
   - Crear routers FastAPI
   - Crear schemas Pydantic v2
   - Implementar `dependencies.py` para extraer contexto de headers

7. **Infraestructura**
   - Configurar `container.py` con inyección de dependencias
   - Configurar logging con structlog

8. **Main + Swagger**
   - Configurar `main.py` con app FastAPI, routers, CORS, lifespan

9. **Tests**
   - Configurar `conftest.py` con DB de test
   - Implementar tests unitarios e integración

10. **Docker**
    - Dockerfile + docker-compose
    - Verificar con `docker-compose up`

---

## Notas arquitectónicas importantes

- **El dominio nunca importa SQLAlchemy ni FastAPI.** Las entidades son dataclasses Python puros.
- **Los repositorios ABC están en el dominio.** Las implementaciones PostgreSQL están en adapters.
- **Los casos de uso reciben repositorios por constructor** (inyección de dependencias manual vía `container.py`).
- **`pool_pre_ping=True` es obligatorio** para compatibilidad con AWS RDS (que cierra conexiones idle).
- **Alembic con async** requiere configuración especial en `env.py` usando `run_sync`. Asegúrate de usar el patrón correcto de migraciones async.
- **No exponer este servicio directamente a Internet.** Solo debe recibir tráfico desde el Gateway (red Docker interna / VPC en AWS).
- **Crear script de seed** para poblar usuarios iniciales sincronizados con el Gateway: mismos IDs, mismos roles. Los clientes de ejemplo se crean desde Atenea con `python manage.py seed_clients`, que POSTea directamente a este servicio.
