import pytest
from backend.phone import (
    format_phone_for_speech,
    mask_phone_number,
    normalize_phone_number,
    words_to_digits,
)


def test_clean_ten_digits():
    ok, norm, err = normalize_phone_number("9876543210")
    assert ok is True
    assert norm == "9876543210"
    assert err == ""


def test_leading_zero():
    ok, norm, err = normalize_phone_number("09876543210")
    assert ok is True
    assert norm == "9876543210"


def test_plus_ninety_one():
    ok, norm, err = normalize_phone_number("+91 98765 43210")
    assert ok is True
    assert norm == "9876543210"

    ok, norm, err = normalize_phone_number("+919876543210")
    assert ok is True
    assert norm == "9876543210"


def test_spoken_digit_words():
    ok, norm, err = normalize_phone_number(
        "nine eight seven six five four three two one zero"
    )
    assert ok is True
    assert norm == "9876543210"


def test_spoken_with_plus_nine_one():
    ok, norm, err = normalize_phone_number(
        "plus nine one nine eight seven six five four three two one zero"
    )
    assert ok is True
    assert norm == "9876543210"


def test_double_multiplier():
    ok, norm, err = normalize_phone_number(
        "double nine eight seven six five four three two one"
    )
    assert ok is True
    assert norm == "9987654321"


def test_dashes_and_spaces():
    ok, norm, err = normalize_phone_number("  987-654-3210  ")
    assert ok is True
    assert norm == "9876543210"


def test_reject_short_number():
    ok, norm, err = normalize_phone_number("987654321")
    assert ok is False
    assert "must be exactly 10 digits" in err


def test_reject_long_number():
    ok, norm, err = normalize_phone_number("9876543210123")
    assert ok is False
    assert "must be exactly 10 digits" in err


def test_reject_invalid_indian_starting_digit():
    ok, norm, err = normalize_phone_number("1234567890")
    assert ok is False
    assert "Standard mobile numbers begin with 6, 7, 8, or 9" in err


def test_format_phone_for_speech():
    formatted = format_phone_for_speech("9876543210")
    assert formatted == "9 8 7 6 5, 4 3 2 1 0"


def test_mask_phone_number():
    masked = mask_phone_number("9876543210")
    assert masked == "••••••3210"
