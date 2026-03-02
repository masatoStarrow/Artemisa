"""
CRM Users Service — FastAPI application entry point.
"""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.adapters.inbound.http.routers.user_router import router as user_router
from src.adapters.inbound.http.routers.client_router import router as client_router
from src.infrastructure.database.connection import engine
from src.infrastructure.logging.setup import setup_logging


logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    setup_logging()
    logger.info("CRM Users Service starting up")
    yield
    await engine.dispose()
    logger.info("CRM Users Service shut down")


app = FastAPI(
    title="CRM Users Service",
    description="Gestión de usuarios del sistema y clientes del CRM. El endpoint POST /users acepta un UUID opcional para sincronización dual-write con el API Gateway.",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Global exception handlers ────────────────────────────────────────────

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": str(exc.errors()),
            },
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception", error=str(exc), exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Error interno del servidor",
            },
        },
    )


# ── Register routers ────────────────────────────────────────────────────
app.include_router(user_router)
app.include_router(client_router)


# ── Health check ─────────────────────────────────────────────────────────

@app.get("/api/v1/health/", tags=["Health"], summary="Health check")
async def health_check():
    """Verifica el estado del servicio y la conexión a la base de datos."""
    from sqlalchemy import text
    from src.infrastructure.database.connection import AsyncSessionLocal

    db_status = "healthy"
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return {
        "success": True,
        "data": {
            "service": "crm-users-service",
            "status": "running",
            "database": db_status,
        },
    }


# ── Development Server ──────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        reload_dirs=["src", "config"],
        log_level="info"
    )
