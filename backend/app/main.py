from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.llm_middleware import LLMConfigMiddleware
from app.api.routes import router
from app.config import settings
from app.db.database import init_db
from app.extraction.llm_config import LLMNotConfiguredError


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="EstudAI",
    description="Assistente de IA para revisão bibliográfica e método científico",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(LLMConfigMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(LLMNotConfiguredError)
async def llm_not_configured_handler(request: Request, exc: LLMNotConfiguredError):
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc), "code": "llm_not_configured"},
    )


app.include_router(router, prefix="/api")
