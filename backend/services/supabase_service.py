from typing import Any

from supabase import Client, create_client

from backend.config import SUPABASE_KEY, SUPABASE_URL

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def save_analysis(data: dict[str, Any]) -> dict[str, Any] | None:
    result = supabase.table("analyses").insert(data).execute()
    return result.data[0] if result.data else None


def get_recent_analyses(limit: int = 5) -> list[dict[str, Any]]:
    result = (
        supabase.table("analyses")
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data if result.data else []
