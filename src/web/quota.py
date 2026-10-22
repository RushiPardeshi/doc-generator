"""Quota and lightweight identity management for Thesis Engine web app."""

import sqlite3
import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from src.config import PROJECT_ROOT

DB_PATH = PROJECT_ROOT / "data" / "quota.db"
MAX_FREE_CLAUDE_PROMPTS = 3


def get_db_connection() -> sqlite3.Connection:
    """Get a SQLite database connection with row factory enabled."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initialize database tables for quota management and audit log."""
    with get_db_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS free_claude_quota (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                fingerprint TEXT,
                client_ip TEXT,
                prompts_used INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used_at TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_quota_email ON free_claude_quota(email);
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_quota_fp ON free_claude_quota(fingerprint);
        """)
        conn.commit()


# Initialize database on module import
init_db()


def normalize_email(email: str) -> str:
    """Normalize email address to lowercase and stripped."""
    return email.strip().lower()


def check_claude_quota(
    email: Optional[str] = None,
    fingerprint: Optional[str] = None,
    client_ip: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Check remaining free Claude prompts for the user.
    Returns:
        allowed: bool
        remaining: int
        used: int
        reason: Optional[str]
    """
    if not email:
        return {
            "allowed": False,
            "remaining": 0,
            "used": 0,
            "reason": "Email required to claim free Claude tier prompts.",
        }

    norm_email = normalize_email(email)

    with get_db_connection() as conn:
        cur = conn.cursor()

        # Check by email
        cur.execute(
            "SELECT prompts_used FROM free_claude_quota WHERE email = ?",
            (norm_email,),
        )
        row = cur.fetchone()

        if row:
            used = row["prompts_used"]
            remaining = max(0, MAX_FREE_CLAUDE_PROMPTS - used)
            if remaining <= 0:
                return {
                    "allowed": False,
                    "remaining": 0,
                    "used": used,
                    "reason": f"Free tier limit reached ({MAX_FREE_CLAUDE_PROMPTS}/{MAX_FREE_CLAUDE_PROMPTS} prompts used). Please provide your Claude API key.",
                }
            return {
                "allowed": True,
                "remaining": remaining,
                "used": used,
                "reason": None,
            }

        # Check by device fingerprint to prevent rapid email spinning on the same device
        if fingerprint:
            cur.execute(
                "SELECT SUM(prompts_used) as total_used FROM free_claude_quota WHERE fingerprint = ?",
                (fingerprint,),
            )
            fp_row = cur.fetchone()
            total_fp_used = fp_row["total_used"] if fp_row and fp_row["total_used"] is not None else 0
            if total_fp_used >= MAX_FREE_CLAUDE_PROMPTS:
                return {
                    "allowed": False,
                    "remaining": 0,
                    "used": total_fp_used,
                    "reason": f"Device free prompt allowance exhausted ({MAX_FREE_CLAUDE_PROMPTS}/{MAX_FREE_CLAUDE_PROMPTS}). Please enter your own Claude API key.",
                }

        return {
            "allowed": True,
            "remaining": MAX_FREE_CLAUDE_PROMPTS,
            "used": 0,
            "reason": None,
        }


def consume_claude_quota(
    email: str,
    fingerprint: Optional[str] = None,
    client_ip: Optional[str] = None,
) -> bool:
    """
    Atomically consume 1 free Claude prompt.
    Returns True if successful, False if quota was exhausted.
    """
    status = check_claude_quota(email, fingerprint, client_ip)
    if not status["allowed"]:
        return False

    norm_email = normalize_email(email)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, prompts_used FROM free_claude_quota WHERE email = ?",
            (norm_email,),
        )
        row = cur.fetchone()

        if row:
            cur.execute(
                """
                UPDATE free_claude_quota 
                SET prompts_used = prompts_used + 1, last_used_at = ?, client_ip = coalesce(?, client_ip), fingerprint = coalesce(?, fingerprint)
                WHERE id = ?
                """,
                (now, client_ip, fingerprint, row["id"]),
            )
        else:
            cur.execute(
                """
                INSERT INTO free_claude_quota (email, fingerprint, client_ip, prompts_used, last_used_at)
                VALUES (?, ?, ?, 1, ?)
                """,
                (norm_email, fingerprint, client_ip, now),
            )
        conn.commit()

    return True
