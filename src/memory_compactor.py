from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def append_event(log_path: str, event: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    payload = dict(event)
    payload.setdefault("ts", _now_iso())
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _iter_events(log_path: str, limit: int = 500) -> Iterable[Dict[str, Any]]:
    if not os.path.exists(log_path):
        return []

    # Read last `limit` lines in a simple way (file is expected small for this project).
    with open(log_path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    out = []
    for line in lines[-limit:]:
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def maybe_compact(
    *,
    log_path: str = "data/session_log.jsonl",
    profile_path: str = "data/learner_profile.md",
    state_manager: Any,
    current_level: str,
    every_n_events: int = 10,
) -> None:
    """
    Simplest compaction:
    - Append events to JSONL during runtime
    - Every N events, write a compact markdown learner profile
    """
    events = list(_iter_events(log_path, limit=800))
    if not events:
        return
    if every_n_events > 0 and (len(events) % every_n_events) != 0:
        return
    write_profile(
        log_path=log_path,
        profile_path=profile_path,
        state_manager=state_manager,
        current_level=current_level,
    )


def write_profile(
    *,
    log_path: str = "data/session_log.jsonl",
    profile_path: str = "data/learner_profile.md",
    state_manager: Any,
    current_level: str,
) -> None:
    events = list(_iter_events(log_path, limit=800))
    topics = getattr(getattr(state_manager, "state", None), "topics", {}) or {}

    # Derive exam history
    last_exam = None
    for ev in reversed(events):
        if ev.get("type") == "exam_result":
            last_exam = ev
            break

    # Sort topics by error count
    topic_rows = []
    for name, st in topics.items():
        try:
            topic_rows.append((name, int(st.errors), int(st.attempts), float(st.mastery)))
        except Exception:
            continue
    topic_rows.sort(key=lambda r: (r[1], r[2]), reverse=True)
    top_focus = [r[0] for r in topic_rows[:2] if r[1] > 0] or [r[0] for r in topic_rows[:1]] or []

    def recommendation_for(topic: str) -> str:
        if topic == "definiteness_mismatch":
            return "Drill indefinite vs definite forms (en/ett vs -en/-et suffix)."
        if topic == "double_definiteness":
            return "Practice: den/det/de + adjective + noun-def (double definiteness)."
        if topic == "article_omission":
            return "Practice adding en/ett for singular count nouns in indefinite contexts."
        if topic == "adjective_agreement":
            return "Practice adjective endings: stor/stort/stora with en/ett + definite/plural."
        return "Practice core Swedish NP patterns."

    recs = "\n".join([f"- {recommendation_for(t)}" for t in top_focus]) if top_focus else "- Keep practicing mixed NPs."

    exam_line = "None yet."
    if last_exam:
        exam_line = f"{last_exam.get('correct')}/{last_exam.get('total')} correct (pass={last_exam.get('passed')})."

    lines = []
    lines.append("# Learner profile (compacted memory)")
    lines.append("")
    lines.append(f"- Last updated (UTC): **{_now_iso()}**")
    lines.append(f"- Current level: **{current_level.upper()}**")
    lines.append(f"- Last exam: **{exam_line}**")
    lines.append(f"- Logged events (last 800): **{len(events)}**")
    lines.append("")
    lines.append("## Current topic stats")
    if topic_rows:
        for name, errors, attempts, mastery in topic_rows:
            lines.append(f"- **{name}**: attempts={attempts}, errors={errors}, mastery={mastery:.2f}")
    else:
        lines.append("- No topic stats yet.")
    lines.append("")
    lines.append("## Recommended focus (next 1–2 sessions)")
    lines.append(recs)
    lines.append("")
    lines.append("## What the agent should remember")
    if top_focus:
        lines.append(f"- The learner most often struggles with: **{', '.join(top_focus)}**.")
    else:
        lines.append("- No strong error pattern yet; continue mixed practice.")
    lines.append("")

    os.makedirs(os.path.dirname(profile_path), exist_ok=True)
    with open(profile_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

