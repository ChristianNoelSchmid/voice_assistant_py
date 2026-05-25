from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Optional

from commands import CommandHandler
from speaker import Speaker
from tasks import TaskClient
from tokens.duration_token import DurationToken
from tokens.duration_token import parse as parse_duration
from tokens.period import PeriodToken, Recurrence, Weekday
from tokens.period import parse as parse_period
from tokens.remind_token import parse as parse_remind
from tokens.time_token import TimeToken
from tokens.time_token import parse as parse_time

_TO_CONTENT = re.compile(r"(?i)\bto\s+(\S.*)")


@dataclass
class RemindMatch:
    """Parsed data extracted from a 'remind me…' utterance."""

    content: str
    period: Optional[PeriodToken]
    time: Optional[TimeToken]
    duration: Optional[DurationToken] = None


class RemindCommand(CommandHandler):
    """Handles 'remind me to X [period] [time]' → creates a task in Vikunja."""

    def __init__(self, client: TaskClient, speaker: Speaker, project_id: int) -> None:
        self._client = client
        self._speaker = speaker
        self._project_id = project_id

    def parse(self, text: str) -> Optional[RemindMatch]:
        """Return a RemindMatch if text contains a remind trigger plus period/time."""
        result = parse_remind(text)
        if result is None:
            return None
        _, remind_span = result
        consumed: list[tuple[int, int]] = []

        period_result = parse_period(text)
        period = None
        if period_result:
            period, span = period_result
            consumed.append(span)

        time_result = parse_time(text)
        time_tok = None
        if time_result:
            time_tok, span = time_result
            consumed.append(span)

        duration_result = parse_duration(text)
        duration = None
        if duration_result:
            duration, span = duration_result
            consumed.append(span)

        # Require at least a period, time, or duration — bare "remind me to X" is rejected.
        if period is None and time_tok is None and duration is None:
            return None

        content = _extract_content(text, remind_span[1], consumed)
        return RemindMatch(
            content=content, period=period, time=time_tok, duration=duration
        )

    def handle(self, match: RemindMatch) -> None:
        print(f'[Remind] "{match.content}"')
        if match.period:
            print(f"  period: {match.period}")
        if match.time:
            print(f"  time: {match.time}")
        if match.duration:
            print(f"  duration: {match.duration}")

        due_date = _compute_due_date(match.period, match.time, match.duration)
        repeat_after, repeat_mode = _compute_repeat(match.period)

        try:
            self._client.create_task(
                match.content,
                due_date,
                repeat_after,
                repeat_mode,
                self._project_id,
            )
            print("[Remind] Task created.")
            self._speaker.speak(f'Created reminder: "{match.content}"')
        except Exception as e:
            print(f"[Remind] Failed to create task: {e}")


def _extract_content(text: str, from_pos: int, consumed: list[tuple[int, int]]) -> str:
    """Collect text from *from_pos* onward, skipping consumed spans, then extract verb phrase after 'to'."""
    spans = sorted([(s, e) for s, e in consumed if e > from_pos], key=lambda x: x[0])
    parts: list[str] = []
    pos = from_pos
    for start, end in spans:
        seg_end = max(start, pos)
        if pos < seg_end:
            parts.append(text[pos:seg_end])
        pos = max(end, pos)
    if pos < len(text):
        parts.append(text[pos:])
    remaining = "".join(parts)
    m = _TO_CONTENT.search(remaining)
    return " ".join(m.group(1).split()) if m else ""


def _compute_due_date(
    period: Optional[PeriodToken],
    time_tok: Optional[TimeToken],
    duration: Optional[DurationToken] = None,
) -> Optional[datetime]:
    """Compute the UTC due date from an optional period, time, or duration offset."""
    if duration is not None:
        return (
            datetime.now().astimezone() + timedelta(seconds=duration.seconds)
        ).astimezone(timezone.utc)

    today = date.today()
    naive_time = time(time_tok.hour, time_tok.minute) if time_tok else time(12, 0)

    if period is None:
        target = today
    elif period.daily:
        target = today
    elif period.weekday is not None:
        target = _next_weekday(today, period.weekday)
    elif period.monthday is not None:
        target = _next_month_day(today, period.monthday)
    else:
        target = today

    local_dt = datetime.combine(target, naive_time).astimezone()
    return local_dt.astimezone(timezone.utc)


def _compute_repeat(
    period: Optional[PeriodToken],
) -> tuple[Optional[int], Optional[int]]:
    """Return (repeat_after, repeat_mode) for the Vikunja API."""
    if period is None or period.recurrence == Recurrence.ONCE:
        return None, None
    if period.recurrence == Recurrence.DAILY:
        return 86400, None
    if period.recurrence == Recurrence.WEEKLY:
        return 604800, None
    if period.recurrence == Recurrence.MONTHLY:
        # repeat_mode=1 tells Vikunja to treat repeat_after as a month count.
        return 1, 1
    return None, None


def _next_weekday(from_date: date, weekday: Weekday) -> date:
    """Return the next occurrence of *weekday* strictly after or on *from_date*."""
    targets = {
        Weekday.MONDAY: 0,
        Weekday.TUESDAY: 1,
        Weekday.WEDNESDAY: 2,
        Weekday.THURSDAY: 3,
        Weekday.FRIDAY: 4,
        Weekday.SATURDAY: 5,
        Weekday.SUNDAY: 6,
    }
    delta = (targets[weekday] - from_date.weekday()) % 7
    return from_date + timedelta(days=delta or 7)


def _next_month_day(from_date: date, day: int) -> date:
    """Return the next occurrence of day-of-month *day*, clamped to valid month lengths."""
    year, month = from_date.year, from_date.month
    last = calendar.monthrange(year, month)[1]
    candidate = date(year, month, min(day, last))
    if candidate >= from_date:
        return candidate
    month += 1
    if month > 12:
        month, year = 1, year + 1
    last = calendar.monthrange(year, month)[1]
    return date(year, month, min(day, last))
