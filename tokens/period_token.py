from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Weekday(Enum):
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


class Month(Enum):
    JANUARY = 0
    FEBRUARY = 1
    MARCH = 2
    APRIL = 3
    MAY = 4
    JUNE = 5
    JULY = 6
    AUGUST = 7
    SEPTEMBER = 8
    OCTOBER = 9
    NOVEMBER = 10
    DECEMBER = 11


class Recurrence(Enum):
    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


@dataclass
class PeriodToken:
    """A scheduling period extracted from an utterance."""

    recurrence: Recurrence
    month: Optional[Month] = None  # january - december, for specific month/day combos
    weekday: Optional[Weekday] = None  # set for weekday-based periods
    monthday: Optional[int] = None  # 1–31, set for monthly periods
    daily: bool = False  # True for "every day"


_WEEKDAY_MAP: dict[str, Weekday] = {
    "monday": Weekday.MONDAY,
    "tuesday": Weekday.TUESDAY,
    "wednesday": Weekday.WEDNESDAY,
    "thursday": Weekday.THURSDAY,
    "friday": Weekday.FRIDAY,
    "saturday": Weekday.SATURDAY,
    "sunday": Weekday.SUNDAY,
}

_MONTH_MAP: dict[str, Month] = {
    "january": Month.JANUARY,
    "february": Month.FEBRUARY,
    "march": Month.MARCH,
    "april": Month.APRIL,
    "may": Month.MAY,
    "june": Month.JUNE,
    "july": Month.JULY,
    "august": Month.AUGUST,
    "september": Month.SEPTEMBER,
    "october": Month.OCTOBER,
    "november": Month.NOVEMBER,
    "december": Month.DECEMBER,
}


_EVERY_DAY = re.compile(r"(?i)\bevery\s+day\b")
_EVERY_WEEKDAY = re.compile(
    r"(?i)\bevery\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b"
)
_ON_WEEKDAY = re.compile(
    r"(?i)\bon\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)(s)?\b"
)
_MONTH_DAY = re.compile(
    r"(?i)(?:\bevery|\bon\s+the)\s+(\d+)(?:st|nd|rd|th)\s+of\s+the\s+month"
)
_MONTH = re.compile(
    r"(?i)\b((january)|(february)|(march)|(april)|(may)|(june)|(july)|(august)|(september)|(october)|(november)|(december))\s+(\d+)(?:st|nd|rd|th)\b"
)


def parse(text: str) -> Optional[tuple[PeriodToken, tuple[int, int]]]:
    """Parse a scheduling period from *text*, returning (token, (start, end)) or None."""
    m = _MONTH.search(text)
    if m:
        month = _MONTH_MAP[m.group(1).lower()]
        day = m.groups()[-1]
        return PeriodToken(
            recurrence=Recurrence.ONCE, month=month, monthday=int(day), daily=False
        ), (
            m.start(),
            m.end(),
        )

    m = _MONTH_DAY

    # "every day" checked before "every [weekday]" to avoid a false match on a hypothetical
    # weekday named "day".
    m = _EVERY_DAY.search(text)
    if m:
        return PeriodToken(recurrence=Recurrence.DAILY, daily=True), (
            m.start(),
            m.end(),
        )

    # Month-day patterns contain "of the month" so they won't collide with weekday patterns.
    m = _MONTH_DAY.search(text)
    if m:
        day = min(max(int(m.group(1)), 1), 31)
        return PeriodToken(recurrence=Recurrence.MONTHLY, monthday=day), (
            m.start(),
            m.end(),
        )

    m = _EVERY_WEEKDAY.search(text)
    if m:
        wd = _WEEKDAY_MAP[m.group(1).lower()]
        return PeriodToken(recurrence=Recurrence.WEEKLY, weekday=wd), (
            m.start(),
            m.end(),
        )

    m = _ON_WEEKDAY.search(text)
    if m:
        wd = _WEEKDAY_MAP[m.group(1).lower()]
        recurrence = Recurrence.WEEKLY if m.group(2) else Recurrence.ONCE
        return PeriodToken(recurrence=recurrence, weekday=wd), (m.start(), m.end())

    return None
