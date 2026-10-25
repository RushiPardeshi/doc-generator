"""Tavily search tool supporting direct REST API and local CLI fallback."""

import json
import os
import shutil
import subprocess
from typing import List, Dict, Any, Optional
import httpx

from src.config import TAVILY_API_KEY


def fetch_tavily_search(
    query: str,
    api_key: Optional[str] = None,
    max_results: int = 5,
) -> List[Dict[str, Any]]:
    """
    Search the live web using Tavily.
    Prefers direct REST API using TAVILY_API_KEY; falls back to the authenticated local tvly CLI.
    """
    key = api_key or TAVILY_API_KEY

    # 1. Direct REST API via API Key
    if key and "mock" not in key.lower():
        try:
            with httpx.Client(timeout=15.0) as client:
                res = client.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": key,
                        "query": query,
                        "max_results": max_results,
                        "include_answer": True,
                    },
                )
                if res.status_code == 200:
                    data = res.json()
                    return data.get("results", [])
        except Exception:
            pass

    # 2. Local CLI Fallback (tvly OAuth session)
    tvly_bin = shutil.which("tvly") or os.path.expanduser("~/.local/bin/tvly")
    if os.path.exists(tvly_bin) and os.access(tvly_bin, os.X_OK):
        try:
            cmd = [tvly_bin, "search", query, "--json"]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if proc.returncode == 0 and proc.stdout.strip():
                data = json.loads(proc.stdout)
                return data.get("results", [])
        except Exception:
            pass

    return []


def format_tavily_dossier(results: List[Dict[str, Any]], topic: str) -> str:
    """Format Tavily search results into a structured factual research dossier."""
    if not results:
        return ""

    lines = [
        f"# Research Dossier: {topic.title()}",
        "",
        "## 1. Executive Summary & Web Findings",
    ]

    for item in results:
        title = item.get("title", "Web Finding").strip()
        url = item.get("url", "")
        content = item.get("content", "").strip()

        lines.append(f"### {title}")
        if url:
            lines.append(f"**Source**: {url}")
        lines.append("")
        lines.append(content)
        lines.append("")

    lines.append("## 2. Key Factual Statements & Quotes")
    lines.append("")
    for i, item in enumerate(results[:5], 1):
        content = item.get("content", "").strip()
        # Extract first 1-2 sentences for factual citation
        first_sentence = content.split(". ")[0] if content else ""
        if first_sentence:
            lines.append(f"{i}. \"{first_sentence}.\" (Source: {item.get('url', 'Tavily Search')})")
    lines.append("")

    return "\n".join(lines)
