from __future__ import annotations

import re

# Each pair is (pattern, replacement). Applied in order — compound forms like
# "twenty first" must appear before their component words.
_NORMALIZATIONS: list[tuple[re.Pattern[str], str]] = [
    # Vosk emits AM/PM as separate letters: "a m" / "p m"
    (re.compile(r"(?i)\ba\s+m\b"), "am"),
    (re.compile(r"(?i)\bp\s+m\b"), "pm"),
    # Compound ordinals — before simple ordinals and cardinals
    (re.compile(r"(?i)\btwenty[\s-]first\b"), "21st"),
    (re.compile(r"(?i)\btwenty[\s-]second\b"), "22nd"),
    (re.compile(r"(?i)\btwenty[\s-]third\b"), "23rd"),
    (re.compile(r"(?i)\btwenty[\s-]fourth\b"), "24th"),
    (re.compile(r"(?i)\btwenty[\s-]fifth\b"), "25th"),
    (re.compile(r"(?i)\btwenty[\s-]sixth\b"), "26th"),
    (re.compile(r"(?i)\btwenty[\s-]seventh\b"), "27th"),
    (re.compile(r"(?i)\btwenty[\s-]eighth\b"), "28th"),
    (re.compile(r"(?i)\btwenty[\s-]ninth\b"), "29th"),
    (re.compile(r"(?i)\bthirty[\s-]first\b"), "31st"),
    (re.compile(r"(?i)\bthirtieth\b"), "30th"),
    (re.compile(r"(?i)\btwentieth\b"), "20th"),
    # Simple ordinals 1st–19th (longer words before shorter where needed)
    (re.compile(r"(?i)\bnineteenth\b"), "19th"),
    (re.compile(r"(?i)\beighteenth\b"), "18th"),
    (re.compile(r"(?i)\bseventeenth\b"), "17th"),
    (re.compile(r"(?i)\bsixteenth\b"), "16th"),
    (re.compile(r"(?i)\bfifteenth\b"), "15th"),
    (re.compile(r"(?i)\bfourteenth\b"), "14th"),
    (re.compile(r"(?i)\bthirteenth\b"), "13th"),
    (re.compile(r"(?i)\btwelfth\b"), "12th"),
    (re.compile(r"(?i)\beleventh\b"), "11th"),
    (re.compile(r"(?i)\btenth\b"), "10th"),
    (re.compile(r"(?i)\bninth\b"), "9th"),
    (re.compile(r"(?i)\beighth\b"), "8th"),
    (re.compile(r"(?i)\bseventh\b"), "7th"),
    (re.compile(r"(?i)\bsixth\b"), "6th"),
    (re.compile(r"(?i)\bfifth\b"), "5th"),
    (re.compile(r"(?i)\bfourth\b"), "4th"),
    (re.compile(r"(?i)\bthird\b"), "3rd"),
    (re.compile(r"(?i)\bsecond\b"), "2nd"),
    (re.compile(r"(?i)\bfirst\b"), "1st"),
    # Cardinals — longer/more-specific before shorter to avoid partial overlaps
    (re.compile(r"(?i)\bnineteen\b"), "19"),
    (re.compile(r"(?i)\beighteen\b"), "18"),
    (re.compile(r"(?i)\bseventeen\b"), "17"),
    (re.compile(r"(?i)\bsixteen\b"), "16"),
    (re.compile(r"(?i)\bfifteen\b"), "15"),
    (re.compile(r"(?i)\bfourteen\b"), "14"),
    (re.compile(r"(?i)\bthirteen\b"), "13"),
    (re.compile(r"(?i)\btwelve\b"), "12"),
    (re.compile(r"(?i)\beleven\b"), "11"),
    (re.compile(r"(?i)\bsixty\b"), "60"),
    (re.compile(r"(?i)\bfifty\b"), "50"),
    (re.compile(r"(?i)\bforty\b"), "40"),
    (re.compile(r"(?i)\bthirty\b"), "30"),
    (re.compile(r"(?i)\btwenty\b"), "20"),
    (re.compile(r"(?i)\bten\b"), "10"),
    (re.compile(r"(?i)\bnine\b"), "9"),
    (re.compile(r"(?i)\beight\b"), "8"),
    (re.compile(r"(?i)\bseven\b"), "7"),
    (re.compile(r"(?i)\bsix\b"), "6"),
    (re.compile(r"(?i)\bfive\b"), "5"),
    (re.compile(r"(?i)\bfour\b"), "4"),
    (re.compile(r"(?i)\bthree\b"), "3"),
    (re.compile(r"(?i)\btwo\b"), "2"),
    (re.compile(r"(?i)\bone\b"), "1"),
    (re.compile(r"(?i)\bzero\b"), "0"),
]


def normalize(text: str) -> str:
    """Convert spoken number words/ordinals to digits and collapse Vosk's spaced AM/PM."""
    for pattern, replacement in _NORMALIZATIONS:
        text = pattern.sub(replacement, text)
    return text
