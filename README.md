# Artemisa — CRM Users & Clients Microservice

Microservicio interno del CRM empresarial responsable de **gestionar usuarios del sistema** y **clientes comerciales**. Es consumido exclusivamente por el API Gateway (Atenea) mediante comunicación HTTP interna en la red Docker.

> **Este servicio no valida JWT ni autenticación.** Confía en los headers internos que inyecta el API Gateway: `X-User-Id`, `X-User-Role`, `X-Request-Id`.

---

## Tabla de contenidos

- [Stack tecnológico](#stack-tecnológico)
- [¿Por qué Clean Architecture (Bancolombia)?](#por-qué-clean-architecture-bancolombia)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Flujo de una petición](#flujo-de-una-petición)
- [Base de datos](#base-de-datos)
- [Endpoints](#endpoints)
- [Contrato de respuestas HTTP](#contrato-de-respuestas-http)
- [Headers internos](#headers-internos-desde-el-gateway)
- [Docker](#docker)
- [Tests](#tests)
- [Documentación API (Swagger)](#documentación-api-swagger)
- [Seed de datos](#seed-de-datos)

---

## Stack tecnológico

| Componente | Tecnología | Versión |
|---|---|---|
| Framework | FastAPI | 0.135 |
| Lenguaje | Python | 3.13 |
| Base de datos | PostgreSQL | 15 (async) |
| ORM | SQLAlchemy 2.0 | + asyncpg |
| Migraciones | Alembic | — |
| Validación | Pydantic v2 | + email-validator |
| Logging | structlog | JSON estructurado |
| Testing | pytest + pytest-asyncio | + httpx |
| Containerización | Docker + docker-compose | — |

---

## ¿Por qué Clean Architecture (Bancolombia)?

Este proyecto sigue los principios de [**Clean Architecture propuestos por Bancolombia**](https://bancolombia.github.io/scaffold-clean-architecture/docs/intro), adaptados de Java/Gradle a Python/FastAPI.

### Motivación

1. **Regla de dependencia:** las capas internas (dominio, aplicación) **no conocen las externas** (FastAPI, SQLAlchemy). Si mañana cambiamos FastAPI por Flask, solo se reescriben los adaptadores — el 100% de la lógica de negocio queda intacta.
2. **Testabilidad:** los casos de uso se prueban con mocks puros — sin necesidad de levantar base de datos ni servidor HTTP.
3. **Separación de responsabilidades:** cada capa tiene un contrato claro. Un nuevo desarrollador sabe exactamente dónde poner código nuevo.
4. **Escalabilidad del equipo:** diferentes personas pueden trabajar en adaptadores, casos de uso y dominio sin pisarse.

### Mapeo Bancolombia → Python

El scaffold de Bancolombia define 4 capas principales. Así se mapean a nuestro proyecto:

| Capa Bancolombia | Módulo Bancolombia | Nuestro equivalente | Qué contiene |
|---|---|---|---|
| **Domain** | `model` | `src/domain/` | Entidades, value objects, puertos (interfaces/ABCs), excepciones |
| **Domain** | `usecase` | `src/application/` | Casos de uso (lógica de negocio) + DTOs de entrada/salida |
| **Infrastructure** | `entry-points` | `src/adapters/inbound/` | Routers FastAPI, schemas Pydantic (reciben HTTP) |
| **Infrastructure** | `driven-adapters` | `src/adapters/outbound/` | Repositorios PostgreSQL con SQLAlchemy (acceden a BD) |
| **Infrastructure** | `helpers` | `src/infrastructure/` | Conexión BD, inyección de dependencias, logging, migraciones |
| **Application** | `app-service` | `main.py` + `config/` | Entry point del servicio, configuración |

### Diagrama de capas

```
┌─────────────────────────────────────────────────────────┐
│                    main.py (FastAPI app)                 │  ← Entry point
├─────────────────────────────────────────────────────────┤
│  adapters/inbound/    │    adapters/outbound/           │  ← Frameworks
│  (HTTP routers)       │    (PostgreSQL repos)           │
├───────────────────────┴─────────────────────────────────┤
│                  application/                            │  ← Python puro
│           (casos de uso + DTOs)                          │
├─────────────────────────────────────────────────────────┤
│                    domain/                               │  ← Python puro
│       (entidades, value objects, ports, excepciones)     │
└─────────────────────────────────────────────────────────┘
         Las flechas de dependencia apuntan hacia adentro →
```

---

## Estructura del proyecto

```
Artemisa/
├── main.py                         # Entry point FastAPI: CORS, routers, exception handlers
├── config/
│   └── settings.py                 # Variables de entorno con pydantic-settings (.env)
├── alembic.ini                     # Config de Alembic (migraciones)
├── requirements.txt                # Dependencias Python
├── Dockerfile                      # Imagen Docker del servicio
├── docker-compose.yml              # users-service (8001) + PostgreSQL (5433)
│
├── src/
│   │
│   ├── domain/                     # 🟢 CAPA DOMINIO — Python puro, CERO frameworks
│   │   │
│   │   ├── entities/               # Representan los objetos principales del negocio
│   │   │   ├── user.py             #   → UserEntity: id, email, full_name, role, is_active,
│   │   │   │                       #                  created_at, updated_at
│   │   │   └── client.py           #   → ClientEntity: id, company, email, phone, status,
│   │   │                           #                    created_at, updated_at
│   │   │
│   │   ├── value_objects/          # Objetos inmutables con validación propia
│   │   │   ├── email.py            #   → Email: valida formato con regex, inmutable
│   │   │   ├── user_role.py        #   → UserRole enum: ADMIN, SOPORTE, COMERCIAL
│   │   │   └── client_status.py    #   → ClientStatus enum: ACTIVE, INACTIVE
│   │   │
│   │   ├── ports/                  # Contratos (interfaces ABC) — definen QUÉ se puede hacer
│   │   │   ├── user_repository.py  #   → ABC con 6 métodos: get_by_id, get_by_email,
│   │   │   │                       #     list_users, create, update, deactivate
│   │   │   └── client_repository.py #  → ABC con 6 métodos: get_by_id, get_by_email,
│   │   │                           #     list_clients, create, update, soft_delete
│   │   │
│   │   └── exceptions.py          # Excepciones de dominio (DomainError base)
│   │                               #   → UserNotFoundError, ClientNotFoundError,
│   │                               #     EmailAlreadyExistsError, ForbiddenError
│   │
│   ├── application/                # 🔵 CAPA APLICACIÓN — Python puro, orquesta la lógica
│   │   │
│   │   ├── dtos/                   # Data Transfer Objects — entrada/salida de los casos de uso
│   │   │   ├── user_dto.py         #   → CreateUserDTO, UpdateUserDTO, UserResponseDTO
│   │   │   └── client_dto.py       #   → CreateClientDTO, UpdateClientDTO
│   │   │
│   │   └── use_cases/              # Cada archivo = 1 caso de uso = 1 acción del negocio
│   │       ├── users/
│   │       │   ├── create_user.py      #   → Validar email único, generar UUID, guardar
│   │       │   ├── get_user.py         #   → Buscar usuario por UUID
│   │       │   ├── list_users.py       #   → Listar con filtros (role, is_active) + paginación
│   │       │   ├── update_user.py      #   → Actualizar campos parcialmente
│   │       │   └── deactivate_user.py  #   → Soft delete: is_active → False
│   │       └── clients/
│   │           ├── create_client.py      # → Validar email único, crear cliente
│   │           ├── get_client.py         # → Buscar cliente por UUID
│   │           ├── list_clients.py       # → Listar con filtro (status) + paginación
│   │           ├── update_client.py      # → Actualizar campos parcialmente
│   │           └── _soft_delete_client.py # → Soft delete: status → 'inactive'
│   │
│   ├── adapters/                   # 🟡 CAPA ADAPTADORES — aquí SÍ se usan frameworks
│   │   │
│   │   ├── inbound/http/           # === Entry Points (reciben peticiones HTTP) ===
│   │   │   ├── dependencies.py     #   → UserContext: extrae X-User-Id, X-User-Role de headers
│   │   │   ├── response_helpers.py #   → success_response(), paginated_response(), error_response()
│   │   │   ├── validators.py       #   → Validaciones compartidas de entrada
│   │   │   ├── routers/
│   │   │   │   ├── user_router.py  #   → /api/v1/users — 5 endpoints CRUD
│   │   │   │   └── client_router.py #  → /api/v1/clients — 5 endpoints CRUD
│   │   │   └── schemas/
│   │   │       ├── user_schema.py  #   → Pydantic v2: CreateUserRequest, UserResponse, etc.
│   │   │       └── client_schema.py #  → Pydantic v2: CreateClientRequest, ClientResponse, etc.
│   │   │
│   │   └── outbound/persistence/   # === Driven Adapters (acceden a BD) ===
│   │       ├── models/
│   │       │   ├── user_model.py   #   → Tabla SQLAlchemy 'users'
│   │       │   └── client_model.py #   → Tabla SQLAlchemy 'clients'
│   │       ├── user_pg_repository.py   # → Implementa UserRepository ABC con SQLAlchemy async
│   │       └── client_pg_repository.py # → Implementa ClientRepository ABC con SQLAlchemy async
│   │
│   └── infrastructure/             # 🟠 HELPERS — utilidades transversales
│       ├── database/
│       │   ├── connection.py       #   → AsyncEngine + get_db() session factory
│       │   └── migrations/         #   → Alembic: versiones de migración de BD
│       ├── di/
│       │   └── container.py        #   → Fábricas de inyección de dependencias (10 factories)
│       │                           #     Cada factory: recibe AsyncSession → retorna use case
│       ├── logging/
│       │   └── setup.py            #   → Configuración structlog (JSON estructurado)
│       └── scripts/
│           └── seed_users.py       #   → [DEPRECADO] Seeding ahora se hace desde Atenea
│
└── tests/
    ├── conftest.py                 # Fixtures: BD SQLite async en memoria, test client, seed data
    ├── unit/
    │   ├── test_create_user.py     #   2 tests — crear usuario + email duplicado
    │   ├── test_assign_agent.py    #  10 tests — create/update/soft-delete clientes
    │   └── test_list_clients.py    #   5 tests — filtros + paginación
    └── integration/
        ├── test_user_endpoints.py  #  10 tests — CRUD usuarios via HTTP
        └── test_client_endpoints.py # 29 tests — CRUD clientes, validaciones, filtros
```

### ¿Qué hace cada capa? (explicación rápida)

| Capa | Carpeta | ¿Importa frameworks? | Responsabilidad |
|---|---|---|---|
| **Dominio** | `src/domain/` | ❌ Python puro | Define las reglas de negocio: qué es un usuario, qué es un cliente, qué errores existen, qué operaciones se pueden hacer (puertos/interfaces) |
| **Aplicación** | `src/application/` | ❌ Python puro | Orquesta los flujos: recibe un DTO, ejecuta validaciones del dominio, llama al repositorio vía el puerto, retorna el resultado |
| **Adaptadores** | `src/adapters/` | ✅ FastAPI, Pydantic, SQLAlchemy | Traduce entre el mundo externo (HTTP, PostgreSQL) y el dominio. Los `inbound` reciben requests HTTP, los `outbound` persisten datos en la BD |
| **Infraestructura** | `src/infrastructure/` | ✅ SQLAlchemy, structlog | Utilidades transversales: conexión a BD, inyección de dependencias, logging estructurado, migraciones |

---

## Flujo de una petición

Para entender cómo fluye una petición real a través de las capas:

```
1. Atenea (Gateway) envía GET /api/v1/clients/?status=active
   con headers: X-User-Id, X-User-Role, X-Request-Id
       │
2. FastAPI router (client_router.py) recibe la petición
       │
3. Dependency (dependencies.py) extrae y valida los headers
       │
4. Router obtiene el caso de uso del contenedor DI (container.py)
       │
5. Caso de uso (list_clients.py) ejecuta la lógica de negocio
   llamando al puerto (ClientRepository ABC)
       │
6. Adaptador outbound (client_pg_repository.py) implementa
   el puerto y ejecuta la query a PostgreSQL con SQLAlchemy
       │
7. Caso de uso retorna la entidad de dominio (ClientEntity)
       │
8. Router serializa con Pydantic (ClientResponse) y envuelve
   en el envelope estándar de respuesta
       │
9. FastAPI retorna el JSON al Gateway (Atenea)
```

---

## Base de datos

> **Nota:** Este servicio **NO almacena contraseñas**. Los passwords se guardan exclusivamente en el API Gateway (Atenea).

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
| `GET` | `/api/v1/users/` | Listar usuarios. Filtros: `role`, `is_active`. Paginación: `page`, `page_size` |
| `POST` | `/api/v1/users/` | Crear usuario (acepta `id` opcional para sincronización dual-write) |
| `GET` | `/api/v1/users/{user_id}` | Obtener usuario por UUID |
| `PUT` | `/api/v1/users/{user_id}` | Actualizar nombre, rol, estado |
| `DELETE` | `/api/v1/users/{user_id}` | Desactivar usuario (soft delete → `is_active=False`) |

### Clientes `/api/v1/clients`

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/v1/clients/` | Listar clientes. Filtro: `status`. Paginación: `page`, `page_size` |
| `POST` | `/api/v1/clients/` | Crear cliente. Campos requeridos: `company`, `email` |
| `GET` | `/api/v1/clients/{client_id}` | Obtener cliente por UUID |
| `PUT` | `/api/v1/clients/{client_id}` | Actualizar datos del cliente |
| `DELETE` | `/api/v1/clients/{client_id}` | Soft delete → `status='inactive'` |

### Health

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/v1/health/` | Verifica conexión a la base de datos |

---

## Contrato de respuestas HTTP

Todas las respuestas siguen el mismo formato envelope:

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

### Excepciones de dominio → códigos HTTP

| Excepción | Código | HTTP |
|---|---|---|
| `UserNotFoundError` | `USER_NOT_FOUND` | 404 |
| `ClientNotFoundError` | `CLIENT_NOT_FOUND` | 404 |
| `EmailAlreadyExistsError` | `EMAIL_ALREADY_EXISTS` | 409 |
| `ForbiddenError` | `FORBIDDEN` | 403 |

---

## Headers internos (desde el Gateway)

Este servicio **no valida JWT**. Confía en los headers que inyecta el API Gateway (Atenea) después de autenticar al usuario:

| Header | Tipo | Ejemplo |
|---|---|---|
| `X-User-Id` | UUID del usuario autenticado | `a1b2c3d4-e5f6-...` |
| `X-User-Role` | Rol del usuario | `admin`, `soporte`, `comercial` |
| `X-Request-Id` | UUID de trazabilidad | `e5f6g7h8-i9j0-...` |

---

## Docker

### Levantar el servicio

```bash
# Opción 1: levantar solo Artemisa
docker-compose up -d --build

# Opción 2: levantar TODO el sistema CRM (recomendado)
cd ../Atenea && ./startup.sh
```

### Comandos útiles

```bash
# Aplicar migraciones
docker-compose exec users-service alembic upgrade head

# Ejecutar tests
docker-compose exec users-service python -m pytest tests/ -v

# Ver logs en tiempo real
docker-compose logs -f users-service
```

### Variables de entorno (`.env`)

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

## Tests

**56 tests** — 0 failures, 0 warnings

```
tests/
├── conftest.py                          # Fixtures: BD SQLite async en memoria, test client
├── unit/
│   ├── test_create_user.py              #  2 tests — crear usuario + email duplicado
│   ├── test_assign_agent.py             # 10 tests — create/update/soft-delete clientes
│   └── test_list_clients.py             #  5 tests — filtros + paginación
└── integration/
    ├── test_user_endpoints.py           # 10 tests — CRUD usuarios via HTTP
    └── test_client_endpoints.py         # 29 tests — CRUD clientes, validaciones, filtros
```

```bash
# Ejecutar tests localmente (sin Docker) — usa SQLite en memoria
python -m pytest tests/ -v --color=yes
```

---

## Documentación API (Swagger)

| URL | Tipo |
|---|---|
| `/api/docs` | Swagger UI (interactivo) |
| `/api/redoc` | ReDoc |
| `/api/openapi.json` | Esquema OpenAPI JSON |

---

## Seed de datos

Los datos iniciales se crean **desde Atenea** (API Gateway), no desde este servicio:

```bash
# Usuarios (dual-write: mismos UUIDs en ambas BDs)
docker-compose exec gateway python manage.py seed_users

# Clientes (POST directo a Artemisa)
docker-compose exec gateway python manage.py seed_clients
```

### Clientes pre-cargados

| Empresa | Email | Status |
|---|---|---|
| Acme Corporation | contacto@acme.com | active |
| Globex Industries | info@globex.com | active |
| Stark Enterprises | ventas@stark.com | active |
| Wayne Technologies | soporte@wayne.com | inactive |
| Umbrella Corp | admin@umbrella.com | active |
