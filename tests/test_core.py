import unicodedata
from datetime import date

import pytest

from habits.core import (
    MAX_NAME_LENGTH,
    ControlCharsError,
    DuplicateHabitError,
    EmptyNameError,
    Habit,
    HabitError,
    InvalidNameError,
    NameTooLongError,
    name_key,
    normalize_name,
    validate_name,
)

CALCULO_NFC = unicodedata.normalize("NFC", "Cálculo")
CALCULO_NFD = unicodedata.normalize("NFD", "Cálculo")


# --- T01: Habit, normalize_name, name_key (RF-1, RF-2) ---


def test_habit_holds_name_and_done_dates() -> None:
    habit = Habit(name="Leer", done_dates={date(2026, 10, 23)})

    assert habit.name == "Leer"
    assert habit.done_dates == {date(2026, 10, 23)}


def test_normalize_name_strips_outer_whitespace_only() -> None:
    assert normalize_name("  Leer 30 minutos \t") == "Leer 30 minutos"
    assert normalize_name("Leer  libro") == "Leer  libro"


def test_normalize_name_keeps_case_and_accents() -> None:
    assert normalize_name(" Repasar Cálculo ") == "Repasar Cálculo"


def test_name_key_ignores_outer_whitespace() -> None:
    assert name_key(" Leer ") == name_key("leer")


def test_name_key_ignores_case_including_non_ascii() -> None:
    assert name_key("ÁRBOL") == name_key("árbol")


def test_name_key_ignores_unicode_normalization_form() -> None:
    assert CALCULO_NFC != CALCULO_NFD
    assert name_key(CALCULO_NFC) == name_key(CALCULO_NFD)


def test_name_key_distinguishes_inner_whitespace() -> None:
    assert name_key("Leer  libro") != name_key("Leer libro")


def test_name_key_distinguishes_accents() -> None:
    assert name_key("Cálculo") != name_key("Calculo")


# --- T02: validate_name and error hierarchy (RF-1, RF-2) ---


def test_error_hierarchy() -> None:
    assert issubclass(InvalidNameError, HabitError)
    assert issubclass(DuplicateHabitError, HabitError)
    for error in (EmptyNameError, NameTooLongError, ControlCharsError):
        assert issubclass(error, InvalidNameError)


def test_max_name_length_is_100() -> None:
    assert MAX_NAME_LENGTH == 100


@pytest.mark.parametrize("name", ["", "   ", " \t "])
def test_validate_name_rejects_empty(name: str) -> None:
    with pytest.raises(EmptyNameError):
        validate_name(name)


def test_validate_name_accepts_exactly_100_characters() -> None:
    validate_name("a" * 100)


def test_validate_name_rejects_101_characters() -> None:
    with pytest.raises(NameTooLongError):
        validate_name("a" * 101)


def test_validate_name_counts_length_in_nfc_form() -> None:
    name = "a" * 99 + unicodedata.normalize("NFD", "á")

    assert len(name) == 101
    validate_name(name)


@pytest.mark.parametrize("name", ["Leer\nlibro", "Leer\tlibro", "Leer\rlibro", "Leer\x00libro"])
def test_validate_name_rejects_control_characters(name: str) -> None:
    with pytest.raises(ControlCharsError):
        validate_name(name)


def test_validate_name_accepts_normalized_name_with_outer_tab() -> None:
    validate_name(normalize_name("\tLeer "))


@pytest.mark.parametrize("name", ["Leer 30 minutos", "Repasar Cálculo", "-x", "Año 2026 ñ"])
def test_validate_name_accepts_regular_names(name: str) -> None:
    validate_name(name)
