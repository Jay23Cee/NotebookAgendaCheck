from __future__ import annotations

from datetime import datetime
from typing import Mapping, Sequence


def tags_summary_text(selected_tags: Sequence[str], *, tag_label_by_key: Mapping[str, str]) -> str:
    if not selected_tags:
        return "Tags: none"
    labels = [tag_label_by_key.get(tag, tag) for tag in selected_tags]
    return f"Tags: {', '.join(labels[:3])}" + ("..." if len(labels) > 3 else "")


def comment_summary_text(
    comment_checks: Sequence[str],
    comment_text: str,
    *,
    max_length: int = 40,
) -> str:
    text = comment_text.strip()
    if not text and comment_checks:
        text = "; ".join(comment_checks)
    if not text:
        return "Comment: None"
    snippet = text[:max_length]
    if len(text) > max_length:
        snippet += "..."
    return f"Comment: {snippet}"


def normalized_check_date(raw_value: str | None) -> str | None:
    value = str(raw_value or "").strip()
    if not value:
        return None
    for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(value, fmt)
            return parsed.strftime("%m/%d/%Y")
        except ValueError:
            continue
    return None

