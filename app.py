from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.core.db import engine, Base
from backend.api.routes import auth, workspaces, calls, admin, templates, simulations


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="Sales Training API",
    description="API for training sales managers",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(workspaces.router)
app.include_router(calls.router)
app.include_router(admin.router)
app.include_router(templates.router)
app.include_router(simulations.router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}