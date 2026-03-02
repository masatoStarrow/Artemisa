# PROMPT — `crm-users-service`

## Contexto general del proyecto

Eres el **microservicio de usuarios** de un CRM empresarial en migración a AWS. Este servicio es responsable exclusivamente de la gestión del perfil de usuarios del sistema: crear, consultar, actualizar y desactivar cuentas. **No emite tokens JWT** — eso es responsabilidad del API Gateway. Recibe todas sus peticiones desde el Gateway, que inyecta headers internos (`X-User-Id`, `X-User-Role`, `X-Request-Id`) en lugar de tokens.

Este servicio también gestiona la **tabla de clientes del CRM**, ya que los clientes son una entidad relacionada con los usuarios (agentes) que los atienden.

---

## Stack tecnológico

| Componente | Tecnología |
|---|---|
| Framework | FastAPI 0.110+ |
| Lenguaje | Python 3.11+ |
| ORM | SQLAlchemy 2.0 async |
| Driver PostgreSQL | asyncpg |
| Migraciones | Alembic |
| Base de datos | PostgreSQL 15 (Docker local → AWS RDS en producción) |
| Validación | Pydantic v2 |
| Documentación | FastAPI nativo (Swagger UI + ReDoc) |
| HTTP Client | httpx (para llamadas futuras a otros servicios) |
| Testing | pytest + pytest-asyncio + httpx AsyncClient |
| Containerización | Docker + docker-compose |
| Variables de entorno | pydantic-settings (BaseSettings) |
| Hashing passwords | passlib + bcrypt |

---

## Arquitectura: Hexagonal (Ports & Adapters)

```
src/
├── domain/                          # DOMINIO PURO — cero imports de frameworks
│   ├── entities/
│   │   ├── user.py                  # @dataclass User: id, email, full_name, role, is_active
│   │   └── client.py                # @dataclass Client: id, full_name, email, phone, company, assigned_agent_id
│   ├── value_objects/
│   │   ├── email.py                 # ValueObject Email con validación
│   │   ├── user_role.py             # Enum: admin, soporte, comercial
│   │   └── client_status.py         # Enum: activo, inactivo, prospecto
│   ├── repositories/
│   │   ├── user_repository.py       # ABC UserRepository
│   │   └── client_repository.py     # ABC ClientRepository
│   └── exceptions.py                # UserNotFoundError, EmailAlreadyExistsError, ClientNotFoundError
│
├── application/                     # CASOS DE USO — solo conoce el dominio
│   ├── use_cases/
│   │   ├── users/
│   │   │   ├── get_user.py          # Buscar por ID
│   │   │   ├── list_users.py        # Listar con filtros y paginación
│   │   │   ├── create_user.py       # Crear + hashear password
│   │   │   ├── update_user.py       # Actualizar perfil
│   │   │   └── deactivate_user.py   # Soft delete (is_active=False)
│   │   └── clients/
│   │       ├── get_client.py
│   │       ├── list_clients.py      # Filtros: estado, agente asignado, empresa
│   │       ├── create_client.py
│   │       ├── update_client.py
│   │       └── assign_agent.py      # Asignar cliente a un agente
│   └── dtos/
│       ├── user_dto.py              # CreateUserDTO, UpdateUserDTO, UserResponseDTO
│       └── client_dto.py            # CreateClientDTO, UpdateClientDTO, ClientResponseDTO
│
├── adapters/
│   ├── inbound/
│   │   └── http/
│   │       ├── routers/
│   │       │   ├── user_router.py   # /users endpoints
│   │       │   └── client_router.py # /clients endpoints
│   │       ├── schemas/
│   │       │   ├── user_schema.py   # Pydantic schemas request/response
│   │       │   └── client_schema.py
│   │       └── dependencies.py      # Extrae X-User-Id, X-User-Role de headers
│   │
│   └── outbound/
│       └── persistence/
│           ├── models/
│           │   ├── user_model.py    # SQLAlchemy ORM Model users
│           │   └── client_model.py  # SQLAlchemy ORM Model clients
│           ├── user_pg_repository.py    # Implementa UserRepository ABC
│           └── client_pg_repository.py  # Implementa ClientRepository ABC
│
└── infrastructure/
    ├── database/
    │   ├── connection.py            # Engine async, SessionLocal, get_db dependency
    │   └── migrations/              # Alembic: env.py, versions/
    ├── logging/
    │   └── setup.py                 # structlog JSON
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
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name         VARCHAR(255) NOT NULL,
    email             VARCHAR(255) UNIQUE NOT NULL,
    phone             VARCHAR(50),
    company           VARCHAR(255),
    status            VARCHAR(20) NOT NULL DEFAULT 'prospecto'
                      CHECK (status IN ('activo','inactivo','prospecto')),
    assigned_agent_id UUID REFERENCES users(id) ON DELETE SET NULL,
    notes             TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Índices de performance
CREATE INDEX idx_clients_assigned_agent ON clients(assigned_agent_id);
CREATE INDEX idx_clients_status ON clients(status);
CREATE INDEX idx_clients_company ON clients(company);
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
| GET | `/api/v1/clients/` | Listar clientes. Filtros: `status`, `assigned_agent_id`, `company`. Paginación | Todos |
| POST | `/api/v1/clients/` | Crear cliente | admin, soporte |
| GET | `/api/v1/clients/{client_id}` | Obtener cliente por ID | Todos |
| PUT | `/api/v1/clients/{client_id}` | Actualizar datos del cliente | admin, soporte |
| DELETE | `/api/v1/clients/{client_id}` | Eliminar cliente (soft delete → status=inactivo) | admin |
| PATCH | `/api/v1/clients/{client_id}/assign` | Asignar agente al cliente | admin |
| GET | `/api/v1/clients/agent/{agent_id}` | Listar clientes asignados a un agente | Todos |

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

// Éxito — objeto único
{
  "success": true,
  "data": { ... }
}

// Error
{
  "success": false,
  "error": {
    "code": "USER_NOT_FOUND",
    "message": "No existe un usuario con ese ID"
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
│   ├── test_create_user.py           # Mock del repository
│   ├── test_list_clients.py          # Filtros y paginación
│   └── test_assign_agent.py          # Asignación de agente a cliente
└── integration/
    ├── test_user_endpoints.py        # CRUD completo de usuarios
    └── test_client_endpoints.py      # CRUD completo de clientes
```

### Configuración de DB de test

```python
# tests/conftest.py
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5433/crm_users_test"

@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
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
- ✅ Crear cliente con datos válidos → 201
- ❌ Crear cliente con email duplicado → 409
- ✅ Listar clientes filtrados por `status=activo`
- ✅ Listar clientes por agente `agent_id`
- ✅ Asignar agente a cliente → 200
- ❌ Asignar agente inexistente → 404
- ✅ Soft delete → `status=inactivo`

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


@router.get("/clients/")
async def list_clients(
    context: UserContext = Depends(get_current_user_context),
    use_case: ListClients = Depends(get_list_clients_use_case),
):
    if context.role == UserRole.COMERCIAL:
        # Comercial solo ve sus clientes asignados
        return await use_case.execute(filters={"assigned_agent_id": context.user_id})
    # Admin y Soporte ven todos
    return await use_case.execute()
```

> **Regla:** autorización → Gateway. Filtrado de datos → microservicio.
---

## Paso a paso de implementación

1. **Setup inicial**
   - `pip install fastapi uvicorn sqlalchemy asyncpg alembic pydantic-settings passlib[bcrypt] pytest pytest-asyncio httpx structlog`
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
- **Crear script de seed** para poblar usuarios iniciales sincronizados con el Gateway: mismos IDs, mismos roles.
