from contextlib import asynccontextmanager
from fastapi import FastAPI

from .models import init_db, close_db
from .routers import router as api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()

app = FastAPI(
    title="Travel API",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(api_router)

@app.get("/")
def read_root() -> dict:
    return {"message": "Hello World"}
