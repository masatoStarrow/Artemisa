# CRM Users Service (Artemisa) — Documentación Completa

## Índice

1. [Descripción General](#1-descripción-general)
2. [Arquitectura del Proyecto](#2-arquitectura-del-proyecto)
3. [Guía de Instalación y Ejecución](#3-guía-de-instalación-y-ejecución)
4. [Comandos — Qué hace cada uno y cuándo usarlo](#4-comandos--qué-hace-cada-uno-y-cuándo-usarlo)
5. [Endpoints de la API](#5-endpoints-de-la-api)
6. [Documentación Swagger (OpenAPI)](#6-documentación-swagger-openapi)
7. [Modelo de Dominio](#7-modelo-de-dominio)
8. [Casos de Uso](#8-casos-de-uso)
9. [Sistema de Headers Internos](#9-sistema-de-headers-internos)
10. [Reglas de Negocio por Rol](#10-reglas-de-negocio-por-rol)
11. [Base de Datos y Migraciones](#11-base-de-datos-y-migraciones)
12. [Variables de Entorno](#12-variables-de-entorno)
13. [Tests](#13-tests)
14. [Estructura de Archivos Explicada](#14-estructura-de-archivos-explicada)
15. [Comunicación con el API Gateway](#15-comunicación-con-el-api-gateway)
16. [Preguntas Frecuentes (FAQ)](#16-preguntas-frecuentes-faq)

---

## 1. Descripción General

El **CRM Users Service** (nombre interno: Artemisa) es un microservicio responsable de la gestión de **usuarios del sistema** y **clientes del CRM**. Es consumido exclusivamente por el API Gateway (Atenea), nunca directamente por clientes frontend.

### Responsabilidades

- **CRUD completo de usuarios** del sistema (admin, soporte, comercial).
- **CRUD completo de clientes** del CRM (prospectos, activos, inactivos).
- **Asignación de agentes** a clientes.
- **Filtrado por rol:** soporte solo ve usuarios activos; comercial solo ve sus clientes asignados.
- **Soft delete:** tanto usuarios como clientes se desactivan, nunca se eliminan físicamente.

### Stack Tecnológico

| Componente | Tecnología | Versión |
|---|---|---|
| Framework | FastAPI | 0.135.1 |
| ORM | SQLAlchemy (async) | 2.0.47 |
| Driver PostgreSQL | asyncpg | 0.31.0 |
| Migraciones | Alembic | 1.18.4 |
| Validación | Pydantic v2 | 2.12.5 |
| Configuración | pydantic-settings | 2.13.1 |
| Logging | structlog | 25.5.0 |
| HTTP Client (tests) | httpx | 0.28.1 |
| Testing | pytest + pytest-asyncio | 9.0.2 / 1.3.0 |
| Containerización | Docker + docker-compose | — |
| Base de datos | PostgreSQL | 15 |
| Python | — | 3.13 |

---

## 2. Arquitectura del Proyecto

Se usa **Arquitectura Hexagonal (Ports & Adapters)**. El dominio (lógica de negocio) es Python puro y no importa ningún framework. FastAPI, SQLAlchemy y Pydantic son detalles de implementación que viven en los adaptadores.

```
┌──────────────────────────────────────────────────────────────┐
│                  API GATEWAY (Atenea)                         │
│        Inyecta headers: X-User-Id, X-User-Role              │
└──────────────────────┬───────────────────────────────────────┘
                       │ HTTP (red Docker interna)
┌──────────────────────▼───────────────────────────────────────┐
│             ADAPTADORES INBOUND (FastAPI Routers)            │
│  UserRouter   → /api/v1/users/*                              │
│  ClientRouter → /api/v1/clients/*                            │
│  HealthCheck  → /api/v1/health/                              │
│  Dependencies → extrae X-User-Id, X-User-Role, X-Request-Id │
└──────────┬───────────────────────────────┬───────────────────┘
           │                               │
┌──────────▼──────────┐     ┌──────────────▼───────────────────┐
│    DOMINIO (CORE)   │     │     ADAPTADORES OUTBOUND         │
│  Entities:          │     │  UserPgRepository (SQLAlchemy)   │
│   - User            │     │  ClientPgRepository (SQLAlchemy) │
│   - Client          │     │                                  │
│  Value Objects:     │     │  PostgreSQL (asyncpg)            │
│   - Email           │     └──────────────────────────────────┘
│   - UserRole        │
│   - ClientStatus    │     ┌──────────────────────────────────┐
│  Use Cases:         │     │       INFRAESTRUCTURA            │
│   - GetUser         │     │  Database connection (async)     │
│   - ListUsers       │     │  Alembic migrations              │
│   - CreateUser      │     │  DI Container (factories)        │
│   - UpdateUser      │     │  Logging (structlog + JSON)      │
│   - DeactivateUser  │     │  Seed script                     │
│   - GetClient       │     └──────────────────────────────────┘
│   - ListClients     │
│   - CreateClient    │
│   - UpdateClient    │
│   - AssignAgent     │
│   - SoftDeleteClient│
│  Ports (ABCs):      │
│   - UserRepository  │
│   - ClientRepository│
│  Exceptions         │
└─────────────────────┘
```

### Las 4 capas

| Capa | Carpeta | Qué contiene | ¿Importa frameworks? |
|---|---|---|---|
| **Dominio (Core)** | `src/domain/` | Entidades (dataclasses), value objects (enums), excepciones, puertos (ABCs) | ❌ Solo Python puro |
| **Aplicación** | `src/application/` | DTOs, casos de uso (orquestan domain + repos) | ❌ Solo Python puro |
| **Adaptadores** | `src/adapters/` | Routers FastAPI, schemas Pydantic, repositories SQLAlchemy | ✅ FastAPI, Pydantic, SQLAlchemy |
| **Infraestructura** | `src/infrastructure/` | Conexión BD, Alembic, DI container, logging, seed | ✅ SQLAlchemy, structlog, Alembic |

### Flujo de una petición

```
1. Gateway envía GET /api/v1/users/ con headers X-User-Id y X-User-Role
2. FastAPI router recibe la petición
3. Dependency get_current_user_context() extrae y valida los headers
4. Router obtiene el use case del DI container (pasando la sesión de BD)
5. Use case ejecuta la lógica de negocio usando el repository (ABC)
6. Repository (implementación PostgreSQL) hace la query a la BD
7. Use case retorna la entidad de dominio
8. Router serializa con Pydantic y envuelve en el formato envelope
9. FastAPI retorna el JSON al Gateway
```

---

## 3. Guía de Instalación y Ejecución

### Requisitos previos
- Docker y Docker Compose instalados
- Git
- Red Docker compartida `crm_network` creada (ver sección 15)

### Paso a paso (primera vez)

```bash
# 1. Clonar el repositorio y entrar al directorio
git clone <url-del-repo>
cd Artemisa

# 2. Crear la red compartida (si no existe aún)
sudo docker network create crm_network

# 3. Copiar variables de entorno
cp .env.example .env

# 4. Construir y levantar los contenedores
sudo docker-compose up --build -d

# 5. Generar la migración inicial de Alembic
sudo docker-compose exec users-service alembic revision --autogenerate -m "initial"

# 6. Aplicar migraciones (crear tablas en la BD)
sudo docker-compose exec users-service alembic upgrade head

# 7. Crear usuarios iniciales de prueba (sincronizados con el Gateway)
sudo docker-compose exec users-service python -m src.infrastructure.scripts.seed_users
```

### Ejecuciones posteriores (ya todo está creado)

```bash
# Solo levantar los servicios (sin reconstruir)
sudo docker-compose up -d
```

> **¿Cuándo necesito `--build`?** Solo cuando cambies el `Dockerfile`, `requirements.txt`, o agregues nuevas dependencias Python. Si solo cambiás código Python, no hace falta `--build` porque el volumen (`.:/app`) sincroniza los archivos automáticamente.

### Detener los servicios

```bash
# Detener (mantiene datos de la BD)
sudo docker-compose down

# Detener y BORRAR TODO (incluyendo BD y volúmenes)
sudo docker-compose down -v
```

### Verificar que funciona

```bash
# Health check
curl http://localhost:8001/api/v1/health/

# Respuesta esperada:
# {"success":true,"data":{"service":"crm-users-service","status":"running","database":"healthy"}}
```

---

## 4. Comandos — Qué hace cada uno y cuándo usarlo

### Comandos Docker

| Comando | Qué hace | ¿Cuándo ejecutarlo? |
|---|---|---|
| `sudo docker-compose up --build -d` | Construye la imagen Docker e inicia users-service + postgres | **Primera vez** o cuando cambies Dockerfile/requirements.txt |
| `sudo docker-compose up -d` | Inicia los servicios sin reconstruir | **Cada vez** que quieras trabajar |
| `sudo docker-compose down` | Detiene los contenedores, mantiene los datos de BD | Cuando termines de trabajar |
| `sudo docker-compose down -v` | Detiene contenedores Y borra la base de datos | Si querés resetear todo desde cero |
| `sudo docker-compose logs -f users-service` | Ver logs del servicio en tiempo real | Para debuggear |
| `sudo docker-compose ps` | Ver el estado de los contenedores | Para verificar que estén corriendo |

### Comandos Alembic (migraciones — se ejecutan DENTRO del contenedor)

| Comando | Qué hace | ¿Cuándo ejecutarlo? |
|---|---|---|
| `sudo docker-compose exec users-service alembic revision --autogenerate -m "descripcion"` | Genera un archivo de migración detectando cambios en los modelos | **Una sola vez** al inicio, o cuando modifiques modelos SQLAlchemy |
| `sudo docker-compose exec users-service alembic upgrade head` | Aplica todas las migraciones pendientes a la BD | **Una sola vez** al inicio, o después de generar nuevas migraciones |
| `sudo docker-compose exec users-service alembic downgrade -1` | Revierte la última migración aplicada | Si necesitás deshacer un cambio de esquema |
| `sudo docker-compose exec users-service alembic history` | Muestra el historial de migraciones | Para ver qué migraciones se han aplicado |
| `sudo docker-compose exec users-service alembic current` | Muestra la migración actual de la BD | Para verificar en qué versión está la BD |

### Comando Seed (datos iniciales)

| Comando | Qué hace | ¿Cuándo ejecutarlo? |
|---|---|---|
| `sudo docker-compose exec users-service python -m src.infrastructure.scripts.seed_users` | Crea 3 usuarios iniciales (admin, soporte, comercial) sincronizados con el Gateway | **Una sola vez** después del primer `alembic upgrade head` |

### Resumen: ¿Qué debo correr siempre?

```
Primera vez:                                    Cada vez que trabajo:
────────────────────────────────               ─────────────────────
docker network create crm_network              docker-compose up -d
docker-compose up --build -d                    (nada más)
alembic revision --autogenerate -m "initial"
alembic upgrade head
python -m src.infrastructure.scripts.seed_users
```

**`revision`, `upgrade` y `seed` son comandos de UNA SOLA VEZ.** Los datos persisten en el volumen Docker `users_postgres_data`. Solo necesitás volver a ejecutarlos si:
- Borrás los volúmenes (`docker-compose down -v`) → repetir los 3 comandos
- Agregás o modificás modelos → solo `revision --autogenerate` + `upgrade head`

---

## 5. Endpoints de la API

### Usuarios (`/api/v1/users/`)

| Método | Ruta | Descripción | Headers requeridos |
|---|---|---|---|
| `GET` | `/api/v1/users/` | Listar usuarios (con filtros y paginación) | X-User-Id, X-User-Role |
| `POST` | `/api/v1/users/` | Crear un nuevo usuario | X-User-Id, X-User-Role |
| `GET` | `/api/v1/users/{user_id}` | Obtener un usuario por su UUID | X-User-Id, X-User-Role |
| `PUT` | `/api/v1/users/{user_id}` | Actualizar datos de un usuario | X-User-Id, X-User-Role |
| `DELETE` | `/api/v1/users/{user_id}` | Desactivar usuario (soft delete: `is_active=false`) | X-User-Id, X-User-Role |

#### Parámetros de query — Listar usuarios (`GET /api/v1/users/`)

| Parámetro | Tipo | Descripción | Default |
|---|---|---|---|
| `role` | string | Filtrar por rol (`admin`, `soporte`, `comercial`) | — |
| `is_active` | boolean | Filtrar por estado activo | — |
| `page` | int (≥1) | Número de página | `1` |
| `page_size` | int (1-100) | Elementos por página | `10` |

### Clientes (`/api/v1/clients/`)

| Método | Ruta | Descripción | Headers requeridos |
|---|---|---|---|
| `GET` | `/api/v1/clients/` | Listar clientes (con filtros y paginación) | X-User-Id, X-User-Role |
| `POST` | `/api/v1/clients/` | Crear un nuevo cliente | X-User-Id, X-User-Role |
| `GET` | `/api/v1/clients/{client_id}` | Obtener un cliente por su UUID | X-User-Id, X-User-Role |
| `PUT` | `/api/v1/clients/{client_id}` | Actualizar datos de un cliente | X-User-Id, X-User-Role |
| `DELETE` | `/api/v1/clients/{client_id}` | Soft delete (cambia status a `inactivo`) | X-User-Id, X-User-Role |
| `PATCH` | `/api/v1/clients/{client_id}/assign` | Asignar un agente a un cliente | X-User-Id, X-User-Role |
| `GET` | `/api/v1/clients/agent/{agent_id}` | Listar clientes por agente asignado | X-User-Id, X-User-Role |

#### Parámetros de query — Listar clientes (`GET /api/v1/clients/`)

| Parámetro | Tipo | Descripción | Default |
|---|---|---|---|
| `status` | string | Filtrar por status (`activo`, `inactivo`, `prospecto`) | — |
| `assigned_agent_id` | UUID | Filtrar por agente asignado | — |
| `company` | string | Buscar por empresa (búsqueda parcial, case-insensitive) | — |
| `page` | int (≥1) | Número de página | `1` |
| `page_size` | int (1-100) | Elementos por página | `10` |

### Health Check

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/v1/health/` | Estado del servicio y conectividad a la base de datos |

### Formato de respuestas

Todas las respuestas siguen el formato **envelope** estándar:

```json
// Éxito simple
{
  "success": true,
  "data": { ... },
  "message": "OK"
}

// Éxito paginado
{
  "success": true,
  "data": {
    "items": [ ... ],
    "total": 25,
    "page": 1,
    "page_size": 10,
    "pages": 3
  }
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

### Códigos de error del dominio

| Código | HTTP Status | Cuándo ocurre |
|---|---|---|
| `USER_NOT_FOUND` | 404 | Se busca un usuario por UUID que no existe |
| `CLIENT_NOT_FOUND` | 404 | Se busca un cliente por UUID que no existe |
| `EMAIL_ALREADY_EXISTS` | 409 | Se intenta crear usuario/cliente con email duplicado |
| `FORBIDDEN` | 403 | El usuario no tiene permisos para la acción |
| `VALIDATION_ERROR` | 422 | Headers faltantes, UUID inválido, datos inválidos |
| `INTERNAL_ERROR` | 500 | Error no controlado del servidor |

### Ejemplos de uso con cURL

```bash
# Listar todos los usuarios (como admin)
curl -s http://localhost:8001/api/v1/users/ \
  -H "X-User-Id: 012d436e-bc57-4bd1-829b-5a6c60e8a57b" \
  -H "X-User-Role: admin"

# Crear un nuevo usuario
curl -s -X POST http://localhost:8001/api/v1/users/ \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 012d436e-bc57-4bd1-829b-5a6c60e8a57b" \
  -H "X-User-Role: admin" \
  -d '{"email": "nuevo@empresa.com", "full_name": "Juan Pérez", "role": "soporte"}'

# Obtener un usuario por ID
curl -s http://localhost:8001/api/v1/users/012d436e-bc57-4bd1-829b-5a6c60e8a57b \
  -H "X-User-Id: 012d436e-bc57-4bd1-829b-5a6c60e8a57b" \
  -H "X-User-Role: admin"

# Actualizar un usuario
curl -s -X PUT http://localhost:8001/api/v1/users/012d436e-bc57-4bd1-829b-5a6c60e8a57b \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 012d436e-bc57-4bd1-829b-5a6c60e8a57b" \
  -H "X-User-Role: admin" \
  -d '{"full_name": "Admin Actualizado", "role": "admin"}'

# Desactivar (soft delete) un usuario
curl -s -X DELETE http://localhost:8001/api/v1/users/012d436e-bc57-4bd1-829b-5a6c60e8a57b \
  -H "X-User-Id: 012d436e-bc57-4bd1-829b-5a6c60e8a57b" \
  -H "X-User-Role: admin"

# Crear un cliente
curl -s -X POST http://localhost:8001/api/v1/clients/ \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 012d436e-bc57-4bd1-829b-5a6c60e8a57b" \
  -H "X-User-Role: admin" \
  -d '{
    "full_name": "Cliente Ejemplo",
    "email": "cliente@empresa.com",
    "phone": "+57300123456",
    "company": "Empresa S.A.",
    "status": "prospecto"
  }'

# Listar clientes filtrados por status
curl -s "http://localhost:8001/api/v1/clients/?status=activo&page=1&page_size=5" \
  -H "X-User-Id: 012d436e-bc57-4bd1-829b-5a6c60e8a57b" \
  -H "X-User-Role: admin"

# Asignar un agente a un cliente
curl -s -X PATCH http://localhost:8001/api/v1/clients/{client_id}/assign \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 012d436e-bc57-4bd1-829b-5a6c60e8a57b" \
  -H "X-User-Role: admin" \
  -d '{"agent_id": "2104bb0a-f8d8-4d3f-99b4-186ad3eb9c47"}'

# Listar clientes de un agente específico
curl -s http://localhost:8001/api/v1/clients/agent/2104bb0a-f8d8-4d3f-99b4-186ad3eb9c47 \
  -H "X-User-Id: 012d436e-bc57-4bd1-829b-5a6c60e8a57b" \
  -H "X-User-Role: admin"

# Soft delete de un cliente (cambia status a "inactivo")
curl -s -X DELETE http://localhost:8001/api/v1/clients/{client_id} \
  -H "X-User-Id: 012d436e-bc57-4bd1-829b-5a6c60e8a57b" \
  -H "X-User-Role: admin"

# Health check
curl -s http://localhost:8001/api/v1/health/
```

---

## 6. Documentación Swagger (OpenAPI)

**Sí, la documentación Swagger está implementada.** FastAPI la genera automáticamente a partir de los type hints, Pydantic schemas y decoradores de los endpoints.

### URLs de documentación

| URL | Interfaz | Descripción |
|---|---|---|
| **http://localhost:8001/api/docs** | Swagger UI | Interfaz interactiva para probar endpoints |
| **http://localhost:8001/api/redoc** | ReDoc | Documentación en formato más legible/estático |
| **http://localhost:8001/api/openapi.json** | OpenAPI JSON | Esquema crudo (para importar en Postman, etc.) |

### Cómo acceder

1. Levantá el proyecto con `docker-compose up -d`
2. Abrí en el navegador: **http://localhost:8001/api/docs**

### Qué vas a ver

- Cada endpoint documentado con su descripción, parámetros de query, request body y respuestas posibles.
- Los endpoints están agrupados por tags: **Users**, **Clients**, **Health**.
- Podés probar los endpoints directamente desde la UI de Swagger.
- **Importante:** como los headers internos (`X-User-Id`, `X-User-Role`) son inyectados por el Gateway, al probar directamente desde Swagger debés incluirlos manualmente. Swagger los mostrará como parámetros de header obligatorios.

### Configuración

La configuración de Swagger está en `main.py`:

```python
app = FastAPI(
    title="CRM Users Service",
    description="Gestión de usuarios del sistema y clientes del CRM.",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)
```

Cada router tiene decoradores de FastAPI (`summary`, `description`, `responses`) que agregan información a la documentación generada:

```python
@router.get(
    "/",
    summary="Listar usuarios",
    description="Lista usuarios con filtros opcionales de rol y estado. Paginación con page y page_size.",
    responses={403: {"description": "Forbidden"}, 422: {"description": "Validation Error"}},
)
async def list_users(...):
```

---

## 7. Modelo de Dominio

### Entidades

Las entidades son **dataclasses Python puras**, sin ninguna dependencia de framework. Son la fuente de verdad de la lógica de negocio.

#### User

```python
@dataclass
class User:
    id: UUID
    email: str
    full_name: str
    role: str               # "admin" | "soporte" | "comercial"
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None
```

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | UUID | Identificador único del usuario |
| `email` | str | Email único del usuario (siempre en minúsculas) |
| `full_name` | str | Nombre completo |
| `role` | str | Rol en el sistema: `admin`, `soporte`, `comercial` |
| `is_active` | bool | Si el usuario está activo (soft delete pone `false`) |
| `created_at` | datetime | Fecha de creación |
| `updated_at` | datetime | Fecha de última actualización |

#### Client

```python
@dataclass
class Client:
    id: UUID
    full_name: str
    email: str
    phone: str | None = None
    company: str | None = None
    status: str = "prospecto"     # "activo" | "inactivo" | "prospecto"
    assigned_agent_id: UUID | None = None
    notes: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
```

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | UUID | Identificador único del cliente |
| `full_name` | str | Nombre completo del cliente |
| `email` | str | Email único del cliente |
| `phone` | str \| None | Teléfono de contacto |
| `company` | str \| None | Empresa a la que pertenece |
| `status` | str | Estado: `activo`, `inactivo`, `prospecto` |
| `assigned_agent_id` | UUID \| None | UUID del usuario (agente) asignado |
| `notes` | str \| None | Notas adicionales sobre el cliente |
| `created_at` | datetime | Fecha de creación |
| `updated_at` | datetime | Fecha de última actualización |

### Value Objects

Los value objects encapsulan validaciones y son inmutables.

#### UserRole (Enum)

```python
class UserRole(str, Enum):
    ADMIN = "admin"
    SOPORTE = "soporte"
    COMERCIAL = "comercial"
```

#### ClientStatus (Enum)

```python
class ClientStatus(str, Enum):
    ACTIVO = "activo"
    INACTIVO = "inactivo"
    PROSPECTO = "prospecto"
```

#### Email (Value Object con validación)

```python
class Email:
    """Inmutable. Valida formato con regex y normaliza a minúsculas."""
    _EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
```

### Excepciones de Dominio

Todas heredan de `DomainError(code, message)`:

| Excepción | Código | Mensaje default | HTTP |
|---|---|---|---|
| `UserNotFoundError` | `USER_NOT_FOUND` | "No existe un usuario con ese ID" | 404 |
| `ClientNotFoundError` | `CLIENT_NOT_FOUND` | "No existe un cliente con ese ID" | 404 |
| `EmailAlreadyExistsError` | `EMAIL_ALREADY_EXISTS` | "Ya existe un registro con ese email" | 409 |
| `ForbiddenError` | `FORBIDDEN` | "No tiene permisos para esta acción" | 403 |

### Puertos (Repositories — ABCs)

Los puertos definen los contratos de acceso a datos. Son **clases abstractas** que el dominio define y los adaptadores outbound implementan.

#### UserRepository

| Método | Firma | Descripción |
|---|---|---|
| `get_by_id` | `(user_id: UUID) → User \| None` | Busca usuario por UUID |
| `get_by_email` | `(email: str) → User \| None` | Busca usuario por email |
| `list_users` | `(role?, is_active?, page, page_size) → (list[User], int)` | Lista con filtros y paginación |
| `create` | `(user: User) → User` | Crea un usuario |
| `update` | `(user: User) → User` | Actualiza un usuario |
| `deactivate` | `(user_id: UUID) → User` | Pone `is_active=False` |

#### ClientRepository

| Método | Firma | Descripción |
|---|---|---|
| `get_by_id` | `(client_id: UUID) → Client \| None` | Busca cliente por UUID |
| `get_by_email` | `(email: str) → Client \| None` | Busca cliente por email |
| `list_clients` | `(status?, assigned_agent_id?, company?, page, page_size) → (list[Client], int)` | Lista con filtros y paginación |
| `list_by_agent` | `(agent_id: UUID, page, page_size) → (list[Client], int)` | Lista clientes por agente |
| `create` | `(client: Client) → Client` | Crea un cliente |
| `update` | `(client: Client) → Client` | Actualiza un cliente |
| `assign_agent` | `(client_id: UUID, agent_id: UUID) → Client` | Asigna agente a cliente |
| `soft_delete` | `(client_id: UUID) → Client` | Pone `status="inactivo"` |

---

## 8. Casos de Uso

Cada caso de uso es una clase con un método `execute()`. Recibe el repository por **inyección de dependencias** en el constructor. Los casos de uso son Python puro y no conocen FastAPI, SQLAlchemy ni Pydantic.

### Usuarios

| Caso de Uso | Archivo | Qué hace |
|---|---|---|
| `GetUser` | `src/application/use_cases/users/get_user.py` | Busca un usuario por UUID. Lanza `UserNotFoundError` si no existe. |
| `ListUsers` | `src/application/use_cases/users/list_users.py` | Lista usuarios con filtros opcionales (`role`, `is_active`) y paginación (`page`, `page_size`). Retorna `(list[User], total_count)`. |
| `CreateUser` | `src/application/use_cases/users/create_user.py` | Valida que el email no exista, genera UUID, normaliza email a minúsculas. Lanza `EmailAlreadyExistsError` si el email ya existe. |
| `UpdateUser` | `src/application/use_cases/users/update_user.py` | Actualiza `full_name`, `role` y/o `is_active`. Solo modifica campos que vienen en el DTO (no-null). Lanza `UserNotFoundError` si no existe. |
| `DeactivateUser` | `src/application/use_cases/users/deactivate_user.py` | Soft delete: pone `is_active=False`. Lanza `UserNotFoundError` si no existe. |

### Clientes

| Caso de Uso | Archivo | Qué hace |
|---|---|---|
| `GetClient` | `src/application/use_cases/clients/get_client.py` | Busca un cliente por UUID. Lanza `ClientNotFoundError` si no existe. |
| `ListClients` | `src/application/use_cases/clients/list_clients.py` | Lista clientes con filtros opcionales (`status`, `assigned_agent_id`, `company`) y paginación. El filtro `company` es búsqueda parcial case-insensitive (ILIKE). |
| `CreateClient` | `src/application/use_cases/clients/create_client.py` | Valida que el email no exista, genera UUID, normaliza email. Lanza `EmailAlreadyExistsError` si el email ya existe. |
| `UpdateClient` | `src/application/use_cases/clients/update_client.py` | Actualiza campos del cliente. Si se cambia el email, verifica que no exista otro cliente con ese email. Lanza `ClientNotFoundError` o `EmailAlreadyExistsError`. |
| `AssignAgent` | `src/application/use_cases/clients/assign_agent.py` | Asigna un agente (usuario) a un cliente. Verifica que **ambos existan** antes de asignar. Lanza `UserNotFoundError` si el agente no existe o `ClientNotFoundError` si el cliente no existe. |
| `SoftDeleteClient` | `src/application/use_cases/clients/_soft_delete_client.py` | Cambia el status del cliente a `"inactivo"`. Lanza `ClientNotFoundError` si no existe. |

### DTOs (Data Transfer Objects)

Los DTOs se usan para pasar datos entre el adaptador inbound y los casos de uso. Son dataclasses simples.

#### User DTOs

```python
@dataclass
class CreateUserDTO:
    email: str
    full_name: str
    role: str

@dataclass
class UpdateUserDTO:
    full_name: str | None = None
    role: str | None = None
    is_active: bool | None = None

@dataclass
class UserResponseDTO:
    id: UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: str
    updated_at: str
```

#### Client DTOs

```python
@dataclass
class CreateClientDTO:
    full_name: str
    email: str
    phone: str | None = None
    company: str | None = None
    status: str = "prospecto"
    assigned_agent_id: UUID | None = None
    notes: str | None = None

@dataclass
class UpdateClientDTO:
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    status: str | None = None
    notes: str | None = None

@dataclass
class ClientResponseDTO:
    id: UUID
    full_name: str
    email: str
    phone: str | None
    company: str | None
    status: str
    assigned_agent_id: UUID | None
    notes: str | None
    created_at: str
    updated_at: str
```

---

## 9. Sistema de Headers Internos

Este microservicio **no tiene autenticación propia**. La autenticación la maneja el API Gateway (Atenea), que valida el JWT del usuario y luego inyecta headers internos en las peticiones que reenvía a Artemisa.

### Headers que el Gateway inyecta

| Header | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `X-User-Id` | UUID (string) | ✅ | ID del usuario autenticado |
| `X-User-Role` | string | ✅ | Rol del usuario (`admin`, `soporte`, `comercial`) |
| `X-Request-Id` | string | ❌ | ID de correlación para trazabilidad (generado por el Gateway) |

### Cómo se extraen

El dependency `get_current_user_context()` en `src/adapters/inbound/http/dependencies.py` se encarga de:

1. Extraer los 3 headers del request.
2. Validar que `X-User-Id` sea un UUID válido → 422 si no.
3. Validar que `X-User-Role` sea un rol válido (`admin`, `soporte`, `comercial`) → 422 si no.
4. Retornar un `UserContext(user_id, role, request_id)`.

```python
@dataclass
class UserContext:
    user_id: UUID
    role: UserRole
    request_id: str
```

Este `UserContext` se inyecta automáticamente en todos los endpoints como dependency de FastAPI:

```python
@router.get("/")
async def list_users(
    context: UserContext = Depends(get_current_user_context),
    ...
):
```

### ¿Qué pasa si no se envían los headers?

FastAPI retorna automáticamente **422 Unprocessable Entity** porque los headers están declarados como obligatorios (`Header(...)`).

---

## 10. Reglas de Negocio por Rol

Las reglas de filtrado por rol se aplican en los **routers** (adaptadores inbound), antes de invocar los casos de uso.

### Rol: Soporte

| Recurso | Restricción |
|---|---|
| Listar usuarios (`GET /users/`) | Solo ve usuarios **activos** (se fuerza `is_active=True`) |

```python
# En user_router.py
if context.role == UserRole.SOPORTE:
    is_active = True  # Fuerza el filtro
```

### Rol: Comercial

| Recurso | Restricción |
|---|---|
| Listar clientes (`GET /clients/`) | Solo ve **sus clientes asignados** (se fuerza `assigned_agent_id=context.user_id`) |

```python
# En client_router.py
if context.role == UserRole.COMERCIAL:
    assigned_agent_id = context.user_id  # Fuerza el filtro
```

### Rol: Admin

| Recurso | Restricción |
|---|---|
| Todo | **Sin restricciones** — acceso total |

### Tabla resumen

| Endpoint | Admin | Soporte | Comercial |
|---|---|---|---|
| `GET /users/` | Todos los usuarios | Solo activos | Todos los usuarios |
| `POST /users/` | ✅ | ✅ | ✅ |
| `GET /users/{id}` | ✅ | ✅ | ✅ |
| `PUT /users/{id}` | ✅ | ✅ | ✅ |
| `DELETE /users/{id}` | ✅ | ✅ | ✅ |
| `GET /clients/` | Todos los clientes | Todos los clientes | Solo sus clientes asignados |
| `POST /clients/` | ✅ | ✅ | ✅ |
| `GET /clients/{id}` | ✅ | ✅ | ✅ |
| `PUT /clients/{id}` | ✅ | ✅ | ✅ |
| `DELETE /clients/{id}` | ✅ | ✅ | ✅ |
| `PATCH /clients/{id}/assign` | ✅ | ✅ | ✅ |

> **Nota:** las restricciones de acceso a nivel de ruta (qué roles pueden acceder a qué endpoints) se manejan en el **API Gateway** (Atenea), no en este servicio. Aquí solo se aplican **filtros de datos** según el rol.

---

## 11. Base de Datos y Migraciones

### Motor y conexión

- **PostgreSQL 15** en Docker (puerto `5433` mapeado al host, `5432` interno).
- **Driver:** `asyncpg` (async nativo, sin bloqueo).
- **ORM:** SQLAlchemy 2.0 con `mapped_column` (estilo declarativo moderno).
- **Tipos UUID:** se usa `sqlalchemy.Uuid` (genérico, compatible tanto con PostgreSQL como con SQLite para tests).

### Esquema de tablas

#### Tabla `users`

| Columna | Tipo SQL | Constraints | Descripción |
|---|---|---|---|
| `id` | UUID | PK | Identificador único |
| `email` | VARCHAR(255) | UNIQUE, NOT NULL | Email del usuario |
| `full_name` | VARCHAR(255) | NOT NULL | Nombre completo |
| `role` | VARCHAR(20) | NOT NULL | Rol: admin/soporte/comercial |
| `is_active` | BOOLEAN | NOT NULL, DEFAULT true | Activo o desactivado |
| `created_at` | TIMESTAMP WITH TZ | NOT NULL, DEFAULT now() | Fecha de creación |
| `updated_at` | TIMESTAMP WITH TZ | NOT NULL, DEFAULT now() | Última actualización |

#### Tabla `clients`

| Columna | Tipo SQL | Constraints | Descripción |
|---|---|---|---|
| `id` | UUID | PK | Identificador único |
| `full_name` | VARCHAR(255) | NOT NULL | Nombre completo del cliente |
| `email` | VARCHAR(255) | UNIQUE, NOT NULL | Email del cliente |
| `phone` | VARCHAR(50) | NULLABLE | Teléfono de contacto |
| `company` | VARCHAR(255) | NULLABLE | Empresa |
| `status` | VARCHAR(20) | NOT NULL, DEFAULT 'prospecto' | activo/inactivo/prospecto |
| `assigned_agent_id` | UUID | FK → users.id (ON DELETE SET NULL), NULLABLE | Agente asignado |
| `notes` | TEXT | NULLABLE | Notas adicionales |
| `created_at` | TIMESTAMP WITH TZ | NOT NULL, DEFAULT now() | Fecha de creación |
| `updated_at` | TIMESTAMP WITH TZ | NOT NULL, DEFAULT now() | Última actualización |

#### Índices

| Índice | Tabla | Columna(s) | Motivo |
|---|---|---|---|
| `idx_clients_assigned_agent` | clients | `assigned_agent_id` | Búsqueda rápida de clientes por agente |
| `idx_clients_status` | clients | `status` | Filtrado frecuente por status |
| `idx_clients_company` | clients | `company` | Búsqueda por empresa |

### Relación entre tablas

```
users (1) ──────< clients (N)
  id        ←── assigned_agent_id (FK, ON DELETE SET NULL)
```

Un usuario puede tener **muchos clientes asignados**. Si el usuario se elimina, el `assigned_agent_id` del cliente pasa a `NULL` (no se pierden los clientes).

### Configuración de la conexión

```python
# src/infrastructure/database/connection.py
engine = create_async_engine(
    settings.database_url,       # postgresql+asyncpg://user:pass@host:port/db
    pool_size=10,                # Conexiones en el pool
    max_overflow=20,             # Conexiones adicionales bajo demanda
    pool_pre_ping=True,          # Verificar conexión antes de usarla
    pool_recycle=3600,           # Reciclar conexiones después de 1 hora
    echo=(settings.app_env == "local"),  # SQL logging en modo local
)
```

### Session management

La dependency `get_db()` provee una sesión por request con commit/rollback automático:

```python
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()       # Auto-commit si no hubo error
        except Exception:
            await session.rollback()     # Auto-rollback si hubo error
            raise
        finally:
            await session.close()
```

### Alembic (migraciones)

- **Config:** `alembic.ini` apunta a `src/infrastructure/database/migrations/`.
- **Async:** el `env.py` usa `async_engine_from_config` con `pool.NullPool` para correr migraciones async.
- **Autogenerate:** importa `Base` y los dos modelos (`UserModel`, `ClientModel`) para que Alembic detecte cambios automáticamente.

```bash
# Generar migración automática
sudo docker-compose exec users-service alembic revision --autogenerate -m "add_phone_field"

# Aplicar migraciones
sudo docker-compose exec users-service alembic upgrade head

# Revertir última migración
sudo docker-compose exec users-service alembic downgrade -1
```

---

## 12. Variables de Entorno

El archivo `.env` controla toda la configuración. Se copia desde `.env.example`:

| Variable | Descripción | Default |
|---|---|---|
| `DB_NAME` | Nombre de la base de datos PostgreSQL | `crm_users_db` |
| `DB_USER` | Usuario de PostgreSQL | `postgres` |
| `DB_PASSWORD` | Contraseña de PostgreSQL | `postgres` |
| `DB_HOST` | Host de la BD (nombre del servicio Docker) | `db` |
| `DB_PORT` | Puerto de PostgreSQL | `5432` |
| `DB_POOL_SIZE` | Tamaño del connection pool | `10` |
| `DB_MAX_OVERFLOW` | Conexiones adicionales permitidas sobre el pool | `20` |
| `APP_ENV` | Entorno de ejecución (`local`, `production`) | `local` |
| `APP_PORT` | Puerto del servicio | `8001` |
| `LOG_LEVEL` | Nivel de logging (`DEBUG`, `INFO`, `WARNING`, `ERROR`) | `INFO` |

### Configuración con pydantic-settings

La clase `Settings` en `config/settings.py` usa `pydantic-settings` para cargar las variables de entorno con **validación de tipos** y **valores por defecto**:

```python
class Settings(BaseSettings):
    db_name: str = "crm_users_db"
    db_user: str = "postgres"
    # ...

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}
```

### Logging

- **Modo local:** `ConsoleRenderer` (colores, legible para humanos).
- **Modo production:** `JSONRenderer` (JSON estructurado, para herramientas como ELK/Datadog).
- Se configura automáticamente según `APP_ENV` al iniciar el servicio.

---

## 13. Tests

### Ejecutar tests

```bash
# Desde el host (con el venv activado)
cd Artemisa
source venv/bin/activate
python -m pytest tests/ -v

# Desde dentro del contenedor Docker
sudo docker-compose exec users-service python -m pytest tests/ -v
```

Los tests usan **SQLite en memoria** (`sqlite+aiosqlite:///:memory:`), así que **no necesitan PostgreSQL** para ejecutarse.

### Estructura de tests

```
tests/
├── conftest.py                          # Fixtures compartidos (BD, client HTTP, seed)
├── unit/
│   ├── test_create_user.py              # 2 tests — lógica de crear usuario
│   ├── test_list_clients.py             # 4 tests — filtros y paginación de clientes
│   └── test_assign_agent.py             # 3 tests — asignación de agente a cliente
└── integration/
    ├── test_user_endpoints.py           # 10 tests — CRUD completo de usuarios via HTTP
    └── test_client_endpoints.py         # 11 tests — CRUD completo de clientes via HTTP
```

### Total: 30 tests (9 unitarios + 21 de integración)

### Qué cubre cada test

**Unit — Create User (2 tests):**
- ✅ Crear usuario exitosamente → retorna email y rol correctos
- ❌ Email duplicado → lanza `EmailAlreadyExistsError`

**Unit — List Clients (4 tests):**
- ✅ Sin filtros → retorna todos los clientes con paginación default
- ✅ Filtro por status → pasa `status="activo"` al repository
- ✅ Paginación → page=3, page_size=5 se pasan correctamente
- ✅ Filtro por agente → pasa `assigned_agent_id` al repository

**Unit — Assign Agent (3 tests):**
- ✅ Asignación exitosa → retorna cliente con `assigned_agent_id` actualizado
- ❌ Agente no existe → lanza `UserNotFoundError`
- ❌ Cliente no existe → lanza `ClientNotFoundError`

**Integration — User Endpoints (10 tests):**
- ✅ `POST /users/` → crear usuario exitoso (201)
- ❌ `POST /users/` → email duplicado (409)
- ✅ `GET /users/?role=soporte` → filtro por rol funciona
- ✅ `GET /users/?page=1&page_size=2` → paginación funciona
- ✅ `GET /users/{id}` → obtener usuario por ID
- ❌ `GET /users/{id}` → usuario no existe (404)
- ✅ `PUT /users/{id}` → actualizar rol
- ✅ `DELETE /users/{id}` → desactivar usuario (`is_active=false`)
- ❌ `GET /users/` sin headers → 422
- ✅ Soporte solo ve usuarios activos

**Integration — Client Endpoints (11 tests):**
- ✅ `POST /clients/` → crear cliente exitoso (201)
- ❌ `POST /clients/` → email duplicado (409)
- ✅ `GET /clients/?status=activo` → filtro por status
- ✅ `GET /clients/agent/{id}` → clientes por agente
- ✅ `GET /clients/{id}` → obtener cliente por ID
- ❌ `GET /clients/{id}` → cliente no existe (404)
- ✅ `PUT /clients/{id}` → actualizar nombre y empresa
- ✅ `DELETE /clients/{id}` → soft delete (status="inactivo")
- ✅ `PATCH /clients/{id}/assign` → asignar agente exitoso
- ❌ `PATCH /clients/{id}/assign` → agente no existe (404)
- ✅ Comercial solo ve sus clientes asignados

### Fixtures principales (`conftest.py`)

| Fixture | Qué hace | Scope |
|---|---|---|
| `setup_db` | Crea y destruye tablas antes/después de cada test (autouse) | function |
| `db_session` | Provee una sesión SQLite async para tests | function |
| `client` | HTTPX AsyncClient con la BD de test inyectada | function |
| `seed_users` | Crea 3 usuarios (admin, soporte, comercial) en la BD de test | function |

### UUIDs fijos para tests

```python
ADMIN_ID    = UUID("00000000-0000-0000-0000-000000000001")
SOPORTE_ID  = UUID("00000000-0000-0000-0000-000000000002")
COMERCIAL_ID = UUID("00000000-0000-0000-0000-000000000003")
```

### Headers de test

```python
INTERNAL_HEADERS_ADMIN = {"X-User-Id": str(ADMIN_ID), "X-User-Role": "admin", ...}
INTERNAL_HEADERS_SOPORTE = {"X-User-Id": str(SOPORTE_ID), "X-User-Role": "soporte", ...}
INTERNAL_HEADERS_COMERCIAL = {"X-User-Id": str(COMERCIAL_ID), "X-User-Role": "comercial", ...}
```

### Nota técnica: SQLAlchemy Uuid

Los modelos usan `sqlalchemy.Uuid` (tipo genérico introducido en SQLAlchemy 2.0) en lugar de `sqlalchemy.dialects.postgresql.UUID`. Esto permite que los tests corran sobre SQLite sin problemas, ya que el tipo genérico se adapta automáticamente al backend.

---

## 14. Estructura de Archivos Explicada

```
Artemisa/
├── main.py                                          # Entry point: FastAPI app, lifespan, CORS, handlers, routers
├── config/
│   └── settings.py                                  # pydantic-settings: BD, App, logging config
├── src/
│   ├── domain/                                      # ── CAPA DOMINIO (Python puro) ──
│   │   ├── entities/
│   │   │   ├── user.py                              # Dataclass User
│   │   │   └── client.py                            # Dataclass Client
│   │   ├── value_objects/
│   │   │   ├── email.py                             # Value object Email (validación regex)
│   │   │   ├── user_role.py                         # Enum: admin, soporte, comercial
│   │   │   └── client_status.py                     # Enum: activo, inactivo, prospecto
│   │   ├── exceptions.py                            # DomainError, UserNotFound, ClientNotFound, etc.
│   │   └── repositories/
│   │       ├── user_repository.py                   # ABC: contrato de acceso a datos de usuarios
│   │       └── client_repository.py                 # ABC: contrato de acceso a datos de clientes
│   │
│   ├── application/                                 # ── CAPA APLICACIÓN (Python puro) ──
│   │   ├── dtos/
│   │   │   ├── user_dto.py                          # CreateUserDTO, UpdateUserDTO, UserResponseDTO
│   │   │   └── client_dto.py                        # CreateClientDTO, UpdateClientDTO, ClientResponseDTO
│   │   └── use_cases/
│   │       ├── users/
│   │       │   ├── get_user.py                      # GetUser: buscar por UUID
│   │       │   ├── list_users.py                    # ListUsers: filtros + paginación
│   │       │   ├── create_user.py                   # CreateUser: validar email, generar UUID
│   │       │   ├── update_user.py                   # UpdateUser: actualizar campos parciales
│   │       │   └── deactivate_user.py               # DeactivateUser: soft delete
│   │       └── clients/
│   │           ├── get_client.py                    # GetClient: buscar por UUID
│   │           ├── list_clients.py                  # ListClients: filtros + paginación
│   │           ├── create_client.py                 # CreateClient: validar email, generar UUID
│   │           ├── update_client.py                 # UpdateClient: actualizar campos parciales
│   │           ├── assign_agent.py                  # AssignAgent: asignar usuario a cliente
│   │           └── _soft_delete_client.py           # SoftDeleteClient: status → inactivo
│   │
│   ├── adapters/                                    # ── CAPA ADAPTADORES ──
│   │   ├── inbound/
│   │   │   └── http/
│   │   │       ├── dependencies.py                  # UserContext: extrae X-User-Id, X-User-Role headers
│   │   │       ├── response_helpers.py              # success_response(), paginated_response(), error_response()
│   │   │       ├── schemas/
│   │   │       │   ├── user_schema.py               # Pydantic: CreateUserRequest, UpdateUserRequest, UserResponse
│   │   │       │   └── client_schema.py             # Pydantic: CreateClientRequest, UpdateClientRequest, ClientResponse
│   │   │       └── routers/
│   │   │           ├── user_router.py               # FastAPI router: /api/v1/users/*
│   │   │           └── client_router.py             # FastAPI router: /api/v1/clients/*
│   │   └── outbound/
│   │       └── persistence/
│   │           ├── models/
│   │           │   ├── user_model.py                # SQLAlchemy: tabla users
│   │           │   └── client_model.py              # SQLAlchemy: tabla clients (FK → users)
│   │           ├── user_pg_repository.py            # Implementación PostgreSQL de UserRepository
│   │           └── client_pg_repository.py          # Implementación PostgreSQL de ClientRepository
│   │
│   └── infrastructure/                              # ── CAPA INFRAESTRUCTURA ──
│       ├── database/
│       │   ├── connection.py                        # Engine async, session factory, Base, get_db dependency
│       │   └── migrations/
│       │       ├── env.py                           # Alembic async config
│       │       ├── script.py.mako                   # Template de migración
│       │       └── versions/
│       │           └── 60b4f25fbe63_initial.py      # Migración inicial (users + clients)
│       ├── di/
│       │   └── container.py                         # Factories de DI: use case + repository assembly
│       ├── logging/
│       │   └── setup.py                             # structlog config (Console local, JSON prod)
│       └── scripts/
│           └── seed_users.py                        # Seed: admin, soporte, comercial
│
├── tests/
│   ├── conftest.py                                  # Fixtures: SQLite in-memory, seed, headers
│   ├── unit/
│   │   ├── test_create_user.py                      # 2 tests unitarios
│   │   ├── test_list_clients.py                     # 4 tests unitarios
│   │   └── test_assign_agent.py                     # 3 tests unitarios
│   └── integration/
│       ├── test_user_endpoints.py                   # 10 tests de integración (HTTP)
│       └── test_client_endpoints.py                 # 11 tests de integración (HTTP)
│
├── docs/
│   └── README.md                                    # Esta documentación
├── .env                                             # Variables de entorno (no se sube a git)
├── .env.example                                     # Template de variables de entorno
├── alembic.ini                                      # Configuración de Alembic
├── pytest.ini                                       # Configuración de pytest
├── requirements.txt                                 # Dependencias Python (pip freeze)
├── Dockerfile                                       # Imagen Docker (python:3.13-slim + uvicorn)
└── docker-compose.yml                               # Servicios: users-service + postgres:15
```

### Inyección de Dependencias (DI Container)

El archivo `src/infrastructure/di/container.py` contiene **funciones factory** que ensamblan cada caso de uso con su implementación de repositorio:

```python
def get_create_user_use_case(db: AsyncSession) -> CreateUser:
    return CreateUser(user_repository=UserPgRepository(db))

def get_assign_agent_use_case(db: AsyncSession) -> AssignAgent:
    return AssignAgent(
        client_repository=ClientPgRepository(db),
        user_repository=UserPgRepository(db),
    )
```

Cada router usa estas factories para obtener los casos de uso:

```python
@router.post("/")
async def create_user(body: CreateUserRequest, db: AsyncSession = Depends(get_db)):
    use_case = get_create_user_use_case(db)  # DI: inyecta repository real
    user = await use_case.execute(dto)
```

### Usuarios seed (sincronizados con el Gateway)

El script `seed_users.py` crea 3 usuarios que coinciden con los del Gateway (Atenea):

| Email | Nombre | Rol |
|---|---|---|
| `admin@crm.com` | Administrador CRM | admin |
| `soporte@crm.com` | Agente Soporte | soporte |
| `comercial@crm.com` | Agente Comercial | comercial |

El script es **idempotente**: si el usuario ya existe (por email), no lo crea de nuevo.

---

## 15. Comunicación con el API Gateway

### Red Docker compartida

Ambos servicios (Atenea y Artemisa) se conectan a una red Docker externa llamada `crm_network`. Esto permite que el Gateway resuelva el hostname `users-service` y se comunique directamente con Artemisa por la red interna, sin pasar por puertos expuestos al host.

```bash
# Crear la red (una sola vez)
sudo docker network create crm_network
```

### Configuración en docker-compose.yml (Artemisa)

```yaml
services:
  users-service:
    networks:
      - default       # Red interna de Artemisa (para hablar con su BD)
      - crm_network   # Red compartida (para que el Gateway lo encuentre)

networks:
  crm_network:
    external: true
```

### Configuración en docker-compose.yml (Atenea/Gateway)

```yaml
services:
  gateway:
    networks:
      - default       # Red interna de Atenea (para hablar con su BD)
      - crm_network   # Red compartida (para encontrar users-service)

networks:
  crm_network:
    external: true
```

### Variable de entorno en el Gateway

```
USERS_SERVICE_URL=http://users-service:8001/api/v1
```

El Gateway accede a los endpoints de Artemisa como:
- `http://users-service:8001/api/v1/users/`
- `http://users-service:8001/api/v1/clients/`
- `http://users-service:8001/api/v1/health/`

### Flujo completo de una petición

```
Frontend → POST /api/v1/auth/login (Gateway:8000)
         ← JWT token

Frontend → GET /api/v1/users/ (Gateway:8000)
           + Authorization: Bearer <token>
         
Gateway  → Valida JWT
         → Extrae user_id, role del token
         → GET http://users-service:8001/api/v1/users/
           + X-User-Id: <uuid>
           + X-User-Role: admin
           + X-Request-Id: <uuid>
         
Artemisa → Extrae headers internos
         → Ejecuta ListUsers use case
         ← JSON response

Gateway  ← Reenvía la respuesta al frontend
Frontend ← Lista de usuarios
```

### Puertos

| Servicio | Puerto interno (Docker) | Puerto externo (host) |
|---|---|---|
| API Gateway (Atenea) | 8000 | 8000 |
| Users Service (Artemisa) | 8001 | 8001 |
| PostgreSQL Gateway | 5432 | 5432 |
| PostgreSQL Users | 5432 | 5433 |

---

## 16. Preguntas Frecuentes (FAQ)

### ¿Por qué este servicio no tiene autenticación propia?

Porque sigue el patrón **API Gateway**. Toda la autenticación (JWT, login, logout) la maneja el Gateway (Atenea). Este servicio solo recibe headers internos (`X-User-Id`, `X-User-Role`) que el Gateway inyecta después de validar el token. Esto simplifica Artemisa y centraliza la seguridad.

### ¿Por qué se usa SQLAlchemy async en vez de sync?

Porque FastAPI es un framework **async-first**. Usar SQLAlchemy async (`asyncpg`) permite que las queries a la BD no bloqueen el event loop, manteniendo el rendimiento óptimo de FastAPI.

### ¿Por qué los modelos usan `sqlalchemy.Uuid` en vez de `sqlalchemy.dialects.postgresql.UUID`?

Para **compatibilidad con SQLite en los tests**. El tipo `sqlalchemy.Uuid` (genérico, introducido en SQLAlchemy 2.0) se adapta automáticamente al backend: usa `UUID` nativo en PostgreSQL y `CHAR(32)` en SQLite. Esto permite correr los 30 tests sobre SQLite en memoria sin necesitar PostgreSQL.

### ¿Por qué hay un `_` antes de `_soft_delete_client.py`?

Es una convención para indicar que este módulo es "interno" o auxiliar. El soft delete es un caso de uso simple que solo cambia el status a "inactivo". El underscore previene que se confunda con los casos de uso principales.

### ¿Cómo agrego un nuevo campo a un modelo?

1. Modificá el modelo en `src/adapters/outbound/persistence/models/` (ej: agregar columna).
2. Actualizá la entidad de dominio en `src/domain/entities/`.
3. Actualizá los DTOs en `src/application/dtos/`.
4. Actualizá los schemas Pydantic en `src/adapters/inbound/http/schemas/`.
5. Generá la migración: `alembic revision --autogenerate -m "add_new_field"`.
6. Aplicá la migración: `alembic upgrade head`.

### ¿Cómo agrego un nuevo caso de uso?

1. Creá el archivo en `src/application/use_cases/`.
2. Usá inyección de dependencias (repository en el constructor).
3. Agregá la factory function en `src/infrastructure/di/container.py`.
4. Usá la factory en el router correspondiente.

### ¿Cómo agrego un nuevo endpoint?

1. Agregá la ruta en el router correspondiente (`user_router.py` o `client_router.py`).
2. Si necesitás un caso de uso nuevo, seguí el proceso anterior.
3. Agregá el schema Pydantic de request/response si es necesario.
4. Escribí tests unitarios y de integración.

### ¿Cómo reseteo la base de datos desde cero?

```bash
sudo docker-compose down -v           # Borra contenedores y volúmenes
sudo docker-compose up --build -d     # Reconstruye y levanta
# Repetir: alembic revision + upgrade + seed
```

### ¿Puedo acceder directo a la base de datos?

Sí, el PostgreSQL de Artemisa está expuesto en el puerto **5433** del host:

```bash
psql -h localhost -p 5433 -U postgres -d crm_users_db
# Password: postgres
```

### ¿Cómo veo los logs del servicio?

```bash
sudo docker-compose logs -f users-service
```

En modo local (`APP_ENV=local`), los logs se muestran en formato legible con colores. En producción, se emiten como JSON estructurado.

### ¿Qué pasa si el Gateway no puede conectarse a este servicio?

El Gateway retorna un error `503 Service Unavailable`:

```json
{
  "success": false,
  "error": {
    "code": "SERVICE_UNAVAILABLE",
    "message": "El servicio de usuarios no está disponible"
  }
}
```

Causas comunes:
1. **Contenedores en redes diferentes** → verificar que ambos estén en `crm_network`.
2. **Servicio no levantado** → `docker-compose up -d`.
3. **URL incorrecta** → verificar `USERS_SERVICE_URL` en el `.env` del Gateway.
