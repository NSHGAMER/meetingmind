import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import get_settings
from .database import init_db
from .errors import HindsightUnavailable, LLMError, LLMInvalidResponse
from .routers import auth, commitments, contacts, dashboard, demo, meetings, memory

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="MeetingMind API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_list,
    allow_origin_regex=r"https://.*\.vercel\.app|http://localhost:\d+|http://127\.0\.0\.1:\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (auth, contacts, meetings, commitments, memory, dashboard, demo):
    app.include_router(r.router)


@app.exception_handler(HindsightUnavailable)
async def _hs(_: Request, e: HindsightUnavailable):
    return JSONResponse(status_code=503, content={"detail": str(e), "code": "hindsight_unavailable"})


@app.exception_handler(LLMInvalidResponse)
async def _llm_invalid(_: Request, e: LLMInvalidResponse):
    return JSONResponse(status_code=502, content={"detail": str(e), "code": "llm_invalid_response"})


@app.exception_handler(LLMError)
async def _llm(_: Request, e: LLMError):
    return JSONResponse(status_code=502, content={"detail": str(e), "code": "llm_error"})


@app.get("/api/health")
@app.get("/health")
def health():
    return {"status": "ok"}
