"""Domain rules for habits and streaks.

Pure module: no file I/O, no clock, no printing. "Today" is always passed in.
"""

import unicodedata
from dataclasses import dataclass, field
from datetime import date

MAX_NAME_LENGTH = 100


class HabitError(Exception):
    """Base class for domain errors. Carries no user-facing text."""


class InvalidNameError(HabitError):
    """The habit name breaks one of the valid-name rules."""


class EmptyNameError(InvalidNameError):
    """The name is empty after stripping outer whitespace."""


class NameTooLongError(InvalidNameError):
    """The name is longer than MAX_NAME_LENGTH characters."""


class ControlCharsError(InvalidNameError):
    """The name contains control characters (Unicode category Cc)."""


class DuplicateHabitError(HabitError):
    """A habit with the same name key already exists."""


@dataclass
class Habit:
    """A habit with its display name and the days it was done."""

    name: str
    done_dates: set[date] = field(default_factory=set)


def normalize_name(raw: str) -> str:
    """Return the display name: the raw name without outer whitespace."""
    return raw.strip()


def name_key(name: str) -> str:
    """Return the comparison key: NFC form, stripped, case-folded."""
    return unicodedata.normalize("NFC", name.strip()).casefold()


def validate_name(name: str) -> None:
    """Raise an InvalidNameError subclass if the display name is not valid.

    Expects a display name (see normalize_name). Length is counted in NFC
    form so the same visible name always has the same length.
    """
    if not name.strip():
        raise EmptyNameError()
    if len(unicodedata.normalize("NFC", name)) > MAX_NAME_LENGTH:
        raise NameTooLongError()
    if any(unicodedata.category(char) == "Cc" for char in name):
        raise ControlCharsError()
