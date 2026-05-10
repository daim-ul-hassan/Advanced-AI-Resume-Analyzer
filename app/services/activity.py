from __future__ import annotations

from datetime import datetime, timezone

from app.models import ActivityEntry
from app.services.storage import load_activity, save_activity


def log_activity(user_id: str, title: str, detail: str) -> ActivityEntry:
    entries = load_activity(user_id)
    entry = ActivityEntry(
        timestamp=datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        title=title,
        detail=detail,
    )
    entries.insert(0, entry.model_dump())
    save_activity(user_id, entries[:60])
    return entry


def get_activity(user_id: str) -> list[ActivityEntry]:
    return [ActivityEntry(**item) for item in load_activity(user_id)]
