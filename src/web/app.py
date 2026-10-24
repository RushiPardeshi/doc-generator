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
from src.web.quota import check_claude_quota, check_provider_quota
from src.web.runner import GenerateRequest, stream_pipeline_execution
from src.research.web_search import compile_research_dossier
from src.routing.classifier import classify_query
from src.routing.models import RoutingDecision
from src.orchestrator import (
    run_thinking_process,
    assemble_content_bundle,
    OrchestratorResult,
    AssembledContentBundle,
)
from src.llm.gemini import GeminiProvider
from src.llm.anthropic import AnthropicProvider
from pydantic import BaseModel


class ThinkRequest(BaseModel):
    query: str
    model_choice: str = "gemini"
    user_gemini_key: Optional[str] = None
    user_claude_key: Optional[str] = None
    serpapi_key: Optional[str] = None
    fmp_key: Optional[str] = None


class BundleRequest(BaseModel):
    query: str
    model_choice: str = "gemini"
    user_gemini_key: Optional[str] = None
    user_claude_key: Optional[str] = None
    serpapi_key: Optional[str] = None
    fmp_key: Optional[str] = None
    generate_output: bool = False

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
    provider: Optional[str] = None,
):
    """Check remaining free Claude or Gemini runs for an email or device fingerprint."""
    client_ip = request.client.host if request.client else None
    prov = (provider or "claude").strip().lower()
    quota = check_provider_quota(provider=prov, email=email, fingerprint=fingerprint, client_ip=client_ip)
    return {
        "max": 3,
        "provider": prov,
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


@app.post("/api/classify", response_model=RoutingDecision)
def classify_endpoint(data: dict):
    """Classify user query into company, topic, industry, comparison, macro, or ambiguous."""
    query = data.get("query", "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query is required.")
    return classify_query(query)


@app.post("/api/think", response_model=OrchestratorResult)
def think_endpoint(req: ThinkRequest):
    """Execute the thinking pipeline: routing, live tool retrieval, template synthesis, and guardrails."""
    if not req.query or not req.query.strip():
        raise HTTPException(status_code=400, detail="Query is required.")

    if req.model_choice == "claude" and req.user_claude_key:
        provider = AnthropicProvider(api_key=req.user_claude_key.strip())
    else:
        provider = GeminiProvider(api_key=req.user_gemini_key.strip() if req.user_gemini_key else None)

    try:
        result = run_thinking_process(
            query=req.query,
            provider=provider,
            serpapi_key=req.serpapi_key,
            fmp_key=req.fmp_key,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/bundle", response_model=AssembledContentBundle)
def bundle_endpoint(req: BundleRequest):
    """
    Assemble the complete combination payload (Routing + Tool Data + Assembled Prompt)
    for inspection or local AI content validation.
    """
    if not req.query or not req.query.strip():
        raise HTTPException(status_code=400, detail="Query is required.")

    provider = None
    if req.generate_output:
        if req.model_choice == "claude" and req.user_claude_key:
            provider = AnthropicProvider(api_key=req.user_claude_key.strip())
        else:
            provider = GeminiProvider(api_key=req.user_gemini_key.strip() if req.user_gemini_key else None)

    try:
        bundle = assemble_content_bundle(
            query=req.query,
            provider=provider,
            serpapi_key=req.serpapi_key,
            fmp_key=req.fmp_key,
            generate_output=req.generate_output,
        )
        return bundle
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
