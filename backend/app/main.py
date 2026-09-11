from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.db import Base, engine
from app.errors import ConflictError, InvalidInputError, NotFoundError
from app.routers import dashboard, employees, kpis, reports, suggestions, tasks


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Chỉ chạy khi server thật khởi động. Test ghi đè get_db sang SQLite
    # in-memory và không vào lifespan, nên không sinh file kpi.db thừa.
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="KPI Weekly Report API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(NotFoundError)
def handle_not_found(request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ConflictError)
def handle_conflict(request: Request, exc: ConflictError) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(InvalidInputError)
def handle_invalid_input(request: Request, exc: InvalidInputError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(employees.router)
app.include_router(kpis.router)
app.include_router(tasks.router)
app.include_router(reports.router)
app.include_router(suggestions.router)
app.include_router(dashboard.router)
