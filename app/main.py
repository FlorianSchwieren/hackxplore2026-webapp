from datetime import UTC, datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.routers import absences, ingest, me, partnerships, predictions, stats, trees, weather
from app.schemas import HealthzResponse

settings = get_settings()

app = FastAPI(title="Baumpate Backend", version="0.1.0")


@app.exception_handler(RuntimeError)
async def runtime_error_handler(_request: Request, exc: RuntimeError) -> JSONResponse:
    if "DATABASE_URL" in str(exc):
        return JSONResponse(
            status_code=503,
            content={"detail": "Database not configured — set DATABASE_URL in .env"},
        )
    return JSONResponse(status_code=500, content={"detail": str(exc)})


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def health_payload() -> dict[str, str]:
    return {"status": "ok", "time": datetime.now(UTC).isoformat()}


@app.get("/healthz", response_model=HealthzResponse)
def root_healthz() -> dict[str, str]:
    return health_payload()


api = FastAPI()


@api.exception_handler(RuntimeError)
async def api_runtime_error_handler(_request: Request, exc: RuntimeError) -> JSONResponse:
    if "DATABASE_URL" in str(exc):
        return JSONResponse(
            status_code=503,
            content={"detail": "Database not configured — set DATABASE_URL in .env"},
        )
    return JSONResponse(status_code=500, content={"detail": str(exc)})


@api.get("/healthz", response_model=HealthzResponse)
def api_healthz() -> dict[str, str]:
    return health_payload()


api.include_router(ingest.router)
api.include_router(trees.router)
api.include_router(partnerships.router)
api.include_router(absences.router)
api.include_router(me.router)
api.include_router(stats.router)
api.include_router(weather.router)
api.include_router(predictions.router)

app.mount(settings.api_prefix, api)
