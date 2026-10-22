"""FastAPI application entrypoint for Thesis Engine web UI."""

import json
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from src.config import PROJECT_ROOT
from src.web.quota import check_claude_quota
from src.web.runner import GenerateRequest, stream_pipeline_execution
from src.research.web_search import compile_research_dossier

app = FastAPI(
    title="Thesis Engine",
    description="Research-to-Conviction Investment Memo Generator",
    version="1.0.0",
)

# Enable CORS for cloud deployment flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TEMPLATES_DIR = PROJECT_ROOT / "src" / "web" / "templates"
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@app.get("/health")
def health_check():
    """Health check endpoint for Render/cloud container monitoring."""
    return {"status": "ok", "app": "Thesis Engine"}


@app.get("/", response_class=HTMLResponse)
def serve_index(request: Request):
    """Serve the main investment memo dashboard."""
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/api/quota")
def get_quota(
    request: Request,
    email: Optional[str] = None,
    fingerprint: Optional[str] = None,
):
    """Check remaining free Claude runs for an email or device fingerprint."""
    client_ip = request.client.host if request.client else None
    quota = check_claude_quota(email=email, fingerprint=fingerprint, client_ip=client_ip)
    return {
        "max": 3,
        **quota,
    }


@app.post("/api/research")
async def compile_dossier_endpoint(data: dict):
    """Compile a research dossier from a topic string."""
    topic = data.get("topic", "").strip()
    if not topic:
        raise HTTPException(status_code=400, detail="Topic is required.")
    gemini_key = data.get("user_gemini_key", "").strip() or None
    try:
        dossier = compile_research_dossier(topic, api_key=gemini_key)
        return {"topic": topic, "dossier": dossier}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate")
async def generate_memo_stream(request: Request, body: GenerateRequest):
    """
    Run pipeline with Server-Sent Events (SSE) streaming progress and outputs.
    """
    client_ip = request.client.host if request.client else None

    async def event_generator():
        async for item in stream_pipeline_execution(body, client_ip=client_ip):
            yield {"data": json.dumps(item)}

    return EventSourceResponse(event_generator())
