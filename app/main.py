from contextlib import asynccontextmanager
from fastapi import FastAPI

from .models import init_db, close_db
from .routers import router as user_router
from .routers import router as province_router


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

app.include_router(user_router)
app.include_router(province_router)

@app.get("/")
def read_root() -> dict:
    return {"message": "Hello World"}
