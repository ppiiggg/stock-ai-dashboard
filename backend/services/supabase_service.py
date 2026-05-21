from typing import Any

from supabase import Client, create_client

from backend.config import SUPABASE_KEY, SUPABASE_URL

_supabase: Client | None = None


def _get_client() -> Client:
    global _supabase
    if _supabase is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set")
        _supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _supabase


def save_analysis(data: dict[str, Any]) -> dict[str, Any] | None:
    result = _get_client().table("analyses").insert(data).execute()
    return result.data[0] if result.data else None


def get_recent_analyses(limit: int = 5) -> list[dict[str, Any]]:
    result = (
        _get_client().table("analyses")
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data if result.data else []
