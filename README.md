# Artemisa — CRM Users & Clients Microservice

Microservicio de gestión de **usuarios** y **clientes** del CRM empresarial. Almacena perfiles de usuario (sincronizados desde el Gateway vía dual-write) y gestiona el CRUD completo de clientes.

---

## Stack tecnológico

| Componente | Tecnología |
|---|---|
| Framework | FastAPI 0.135 |
| Lenguaje | Python 3.13 |
| Base de datos | PostgreSQL 15 (async) |
| ORM | SQLAlchemy 2.0 + asyncpg |
| Migraciones | Alembic |
| Validación | Pydantic v2 + email-validator |
| Testing | pytest + pytest-asyncio + httpx |
| Containerización | Docker + docker-compose |

---

## Arquitectura hexagonal

```
src/
├── domain/                                    # DOMINIO — cero imports de frameworks
│   ├── entities/
│   │   ├── user.py                            # UserEntity: id, email, full_name, role, is_active
│   │   └── client.py                          # ClientEntity: id, company, email, phone, status
│   ├── value_objects/
│   │   ├── user_role.py                       # UserRole enum: admin, soporte, comercial
│   │   ├── client_status.py                   # ClientStatus enum: active, inactive
│   │   └── email.py                           # Email value object
│   ├── repositories/
│   │   ├── user_repository.py                 # ABC: get_by_id, get_by_email, list, create, update, deactivate
│   │   └── client_repository.py               # ABC: get_by_id, get_by_email, list, create, update, soft_delete
│   └── exceptions.py                          # DomainError, UserNotFound, ClientNotFound, EmailAlreadyExists, Forbidden
│
├── application/
│   ├── dtos/
│   │   ├── user_dto.py                        # CreateUserDTO, UpdateUserDTO
│   │   └── client_dto.py                      # CreateClientDTO, UpdateClientDTO
│   └── use_cases/
│       ├── users/
│       │   ├── create_user.py
│       │   ├── get_user.py
│       │   ├── list_users.py
│       │   ├── update_user.py
│       │   └── deactivate_user.py
│       └── clients/
│           ├── create_client.py
│           ├── get_client.py
│           ├── list_clients.py
│           ├── update_client.py
│           └── _soft_delete_client.py         # DELETE → status = 'inactive'
│
├── adapters/
│   ├── inbound/http/
│   │   ├── dependencies.py                    # UserContext from X-User-Id/X-User-Role headers
│   │   ├── response_helpers.py                # success_response, paginated_response, error_response
│   │   ├── validators.py
│   │   ├── routers/
│   │   │   ├── user_router.py                 # /api/v1/users (5 endpoints)
│   │   │   └── client_router.py               # /api/v1/clients (5 endpoints)
│   │   └── schemas/
│   │       ├── user_schema.py                 # Pydantic request/response schemas
│   │       └── client_schema.py               # CreateClientRequest, UpdateClientRequest, ClientResponse
│   └── outbound/persistence/
│       ├── models/
│       │   ├── user_model.py                  # SQLAlchemy User model
│       │   └── client_model.py                # SQLAlchemy Client model (company NOT NULL, status default 'active')
│       ├── user_pg_repository.py
│       └── client_pg_repository.py            # Implements ClientRepository ABC
│
└── infrastructure/
    ├── database/
    │   ├── connection.py                      # AsyncEngine, get_db session factory
    │   └── migrations/versions/               # Alembic migrations
    ├── di/container.py                        # Dependency injection factories
    └── logging/setup.py
```

---

## Esquema de base de datos

### Tabla `users`

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

CREATE INDEX idx_clients_status ON clients(status);
```

---

## Endpoints

### Usuarios `/api/v1/users`

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/v1/users/` | Listar usuarios. Filtros: `role`, `is_active`. Paginación: `page`, `page_size` |
| POST | `/api/v1/users/` | Crear usuario |
| GET | `/api/v1/users/{user_id}` | Obtener usuario por ID |
| PUT | `/api/v1/users/{user_id}` | Actualizar nombre, rol, estado |
| DELETE | `/api/v1/users/{user_id}` | Desactivar usuario (soft delete → `is_active=False`) |

### Clientes `/api/v1/clients`

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/v1/clients/` | Listar clientes. Filtro: `status`. Paginación: `page`, `page_size` |
| POST | `/api/v1/clients/` | Crear cliente. Campos requeridos: `company`, `email` |
| GET | `/api/v1/clients/{client_id}` | Obtener cliente por ID |
| PUT | `/api/v1/clients/{client_id}` | Actualizar datos del cliente |
| DELETE | `/api/v1/clients/{client_id}` | Eliminar cliente (soft delete → `status='inactive'`) |

### Health

| Método | Ruta |
|---|---|
| GET | `/api/v1/health/` |

---

## Contrato de respuestas HTTP

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
  "data": {
    "id": "uuid",
    "company": "Acme Corporation",
    "email": "contacto@acme.com",
    "phone": "+1-555-100-2000",
    "status": "active",
    "created_at": "2025-01-01T00:00:00Z",
    "updated_at": "2025-01-01T00:00:00Z"
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

### Códigos de error

| Excepción | Código | HTTP |
|---|---|---|
| `UserNotFoundError` | `USER_NOT_FOUND` | 404 |
| `ClientNotFoundError` | `CLIENT_NOT_FOUND` | 404 |
| `EmailAlreadyExistsError` | `EMAIL_ALREADY_EXISTS` | 409 |
| `ForbiddenError` | `FORBIDDEN` | 403 |

---

## Headers internos (desde el Gateway)

Este servicio **no valida JWT**. Confía en los headers que inyecta el API Gateway (Atenea):

```
X-User-Id: <uuid>
X-User-Role: admin|soporte|comercial
X-Request-Id: <uuid>
```

---

## Docker

```bash
# Levantar
docker-compose up -d --build

# Migraciones
docker-compose exec users-service alembic upgrade head

# Tests
docker-compose exec users-service python -m pytest tests/ -v

# Logs
docker-compose logs -f users-service
```

### Variables de entorno (.env)

```env
DB_NAME=crm_users_db
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=db
DB_PORT=5432
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
APP_ENV=local
APP_PORT=8001
LOG_LEVEL=INFO
```

---

## Documentación API (Swagger)

| URL | Tipo |
|---|---|
| `/api/docs` | Swagger UI |
| `/api/redoc` | ReDoc |
| `/api/openapi.json` | OpenAPI JSON |

---

## Tests

**56 tests** — 0 failures

```
tests/
├── conftest.py                          # Fixtures: async DB, test client, seed data
├── unit/
│   ├── test_assign_agent.py             # 10 tests — Create/Update/SoftDelete use cases
│   └── test_list_clients.py             # 5 tests — ListClients use case
└── integration/
    ├── test_user_endpoints.py           # 11 tests — user CRUD endpoints
    └── test_client_endpoints.py         # 30 tests — client CRUD, validations, pagination, filters
```

---

## Seed de datos

Los clientes de ejemplo se crean desde Atenea (Gateway) usando el management command `seed_clients`, que POSTea directamente a este servicio:

| Empresa | Email | Status |
|---|---|---|
| Acme Corporation | contacto@acme.com | active |
| Globex Industries | info@globex.com | active |
| Stark Enterprises | ventas@stark.com | active |
| Wayne Technologies | soporte@wayne.com | inactive |
| Umbrella Corp | admin@umbrella.com | active |
