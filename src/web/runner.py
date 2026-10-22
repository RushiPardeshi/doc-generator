"""Pipeline execution runner with asynchronous SSE queue streaming."""

import asyncio
from typing import AsyncGenerator, Optional, Dict, Any
from pydantic import BaseModel

from src.pipeline import run_pipeline, PipelineConfig, PipelineResult
from src.llm.anthropic import AnthropicProvider
from src.llm.gemini import GeminiProvider
from src.llm.base import LLMProvider
from src.research.web_search import compile_research_dossier
from src.web.quota import check_claude_quota, consume_claude_quota


class GenerateRequest(BaseModel):
    topic: str
    dossier_text: Optional[str] = None
    company_name: Optional[str] = None
    model_choice: str = "gemini"  # "gemini" or "claude"
    user_gemini_key: Optional[str] = None
    user_claude_key: Optional[str] = None
    user_email: Optional[str] = None
    fingerprint: Optional[str] = None
    enable_debate: bool = True
    enable_voice: bool = True


async def stream_pipeline_execution(
    req: GenerateRequest,
    client_ip: Optional[str] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Run dossier generation and the Thesis Engine pipeline, streaming real-time
    progress events, candidate theses, and the final memo over SSE.
    """
    loop = asyncio.get_running_loop()
    event_queue: asyncio.Queue = asyncio.Queue()

    # 1. Resolve LLM Provider & Enforce Quota
    provider: LLMProvider
    if req.model_choice == "claude":
        if req.user_claude_key and req.user_claude_key.strip():
            # BYOK Claude: unlimited
            provider = AnthropicProvider(api_key=req.user_claude_key.strip())
        else:
            # Free tier Claude: check and consume quota
            if not req.user_email or not req.user_email.strip():
                yield {
                    "event": "error",
                    "message": "Email address is required to claim the free Claude tier runs.",
                }
                return

            quota = check_claude_quota(req.user_email, req.fingerprint, client_ip)
            if not quota["allowed"]:
                yield {
                    "event": "error",
                    "message": quota["reason"] or "Free Claude quota exhausted. Please enter your Anthropic API key.",
                }
                return

            # Consume 1 prompt
            consumed = consume_claude_quota(req.user_email, req.fingerprint, client_ip)
            if not consumed:
                yield {
                    "event": "error",
                    "message": "Unable to claim free prompt. Free quota exhausted.",
                }
                return

            try:
                provider = AnthropicProvider()
            except Exception as e:
                yield {
                    "event": "error",
                    "message": f"Server Claude provider error: {str(e)}",
                }
                return
    else:
        # Default Gemini: free
        gemini_key = req.user_gemini_key.strip() if req.user_gemini_key and req.user_gemini_key.strip() else None
        try:
            provider = GeminiProvider(api_key=gemini_key)
        except Exception as e:
            yield {
                "event": "error",
                "message": f"Gemini provider error: {str(e)}",
            }
            return

    # 2. Topic Dossier Resolution
    dossier_content = req.dossier_text.strip() if req.dossier_text and req.dossier_text.strip() else ""
    company = req.company_name.strip() if req.company_name and req.company_name.strip() else req.topic.strip()

    if not dossier_content:
        yield {
            "event": "progress",
            "stage_key": "research_start",
            "message": f"Initiating live web research for '{req.topic}' using Search Grounding...",
            "step": 0,
            "total_steps": 4,
            "data": None,
        }
        try:
            gemini_key = req.user_gemini_key.strip() if req.user_gemini_key and req.user_gemini_key.strip() else None
            dossier_content = await loop.run_in_executor(
                None,
                compile_research_dossier,
                req.topic,
                gemini_key,
                None,
            )
            yield {
                "event": "progress",
                "stage_key": "research_done",
                "message": f"Successfully compiled empirical research dossier ({len(dossier_content)} characters).",
                "step": 0,
                "total_steps": 4,
                "data": {"dossier_preview": dossier_content[:600] + "..."},
            }
        except Exception as e:
            yield {
                "event": "error",
                "message": f"Automated web research failed: {str(e)}. If free Gemini quota is resting, please paste your research dossier directly or provide an API key.",
            }
            return

    # 3. Synchronous Pipeline Execution in Background Thread
    def progress_callback(stage_key: str, message: str, step: int, total_steps: int, data: Optional[Dict[str, Any]] = None):
        loop.call_soon_threadsafe(
            event_queue.put_nowait,
            {
                "event": "progress",
                "stage_key": stage_key,
                "message": message,
                "step": step,
                "total_steps": total_steps,
                "data": data,
            },
        )

    pipe_cfg = PipelineConfig(
        company_name=company,
        enable_debate=req.enable_debate,
        enable_voice=req.enable_voice,
    )

    pipeline_future = loop.run_in_executor(
        None,
        run_pipeline,
        dossier_content,
        provider,
        pipe_cfg,
        progress_callback,
    )

    # 4. Stream events from queue until pipeline completes
    while not pipeline_future.done():
        try:
            event = await asyncio.wait_for(event_queue.get(), timeout=0.5)
            yield event
        except asyncio.TimeoutError:
            # Yield heartbeat to keep SSE connection alive on cloud proxies
            yield {"event": "ping"}

    # Drain remaining events from queue
    while not event_queue.empty():
        yield event_queue.get_nowait()

    # 5. Handle Final Result or Exception
    try:
        result: PipelineResult = await pipeline_future
        yield {
            "event": "complete",
            "message": "Investment memo generation successfully completed.",
            "data": {
                "company_name": result.company_name,
                "final_memo": result.final_memo,
                "verified_claims_count": len(result.verified_claims),
                "slop_score": result.lint_result.slop_score,
                "traceability_passed": result.traceability_report.is_valid,
                "theses": [t.model_dump() for t in (result.candidate_theses or [])],
                "debate_summary": result.debate_result.arbitration_summary if result.debate_result else None,
            },
        }
    except Exception as e:
        yield {
            "event": "error",
            "message": f"Pipeline failure: {str(e)}",
        }

    yield {"event": "done"}
