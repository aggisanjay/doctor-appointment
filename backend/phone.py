import re
from typing import Tuple

WORD_TO_DIGIT = {
    "zero": "0",
    "oh": "0",
    "o": "0",
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",
}

MULTIPLIERS = {
    "double": 2,
    "triple": 3,
}


def words_to_digits(text: str) -> str:
    """Convert spoken number words (including double/triple multipliers) to digit strings."""
    tokens = re.findall(r"[A-Za-z0-9+]+", text.lower())
    result_chars = []
    i = 0
    while i < len(tokens):
        token = tokens[i]

        # Handle "plus nine one" or "+91"
        if token == "plus":
            result_chars.append("+")
            i += 1
            continue

        if token in MULTIPLIERS and i + 1 < len(tokens):
            multiplier = MULTIPLIERS[token]
            next_token = tokens[i + 1]
            if next_token in WORD_TO_DIGIT:
                result_chars.append(WORD_TO_DIGIT[next_token] * multiplier)
                i += 2
                continue
            elif next_token.isdigit() and len(next_token) == 1:
                result_chars.append(next_token * multiplier)
                i += 2
                continue

        if token in WORD_TO_DIGIT:
            result_chars.append(WORD_TO_DIGIT[token])
        elif token.isdigit() or (token.startswith("+") and token[1:].isdigit()):
            result_chars.append(token)
        else:
            # Check if token contains digits mixed with characters, e.g. "+91"
            digits = re.sub(r"[^\d+]", "", token)
            if digits:
                result_chars.append(digits)
        i += 1

    return "".join(result_chars)


def normalize_phone_number(raw_input: str) -> Tuple[bool, str, str]:
    """
    Normalizes a spoken or typed phone number to an exact 10-digit Indian mobile number.
    
    Accepts:
    - 10-digit numbers (e.g. "9876543210")
    - Leading "+91" or "91" (e.g. "+919876543210" or "+91 98765 43210")
    - Leading "0" (e.g. "09876543210")
    - Spoken words (e.g. "nine eight seven six five four three two one zero")
    - Common phrases like "double nine", "plus nine one"
    
    Returns:
        (is_valid, normalized_phone, error_message)
    """
    if not raw_input or not str(raw_input).strip():
        return False, "", "Phone number cannot be empty."

    raw_str = str(raw_input).strip()

    # Step 1: Convert word representations to digits
    converted = words_to_digits(raw_str)

    # Step 2: Strip any non-digit characters except leading '+'
    cleaned = re.sub(r"[^\d+]", "", converted)

    # Remove leading "+" if present
    if cleaned.startswith("+"):
        cleaned = cleaned[1:]

    # Step 3: Handle country code 91 or leading 0
    # If 12 digits and starts with 91, strip 91
    if len(cleaned) == 12 and cleaned.startswith("91"):
        cleaned = cleaned[2:]
    # If 11 digits and starts with 0, strip leading 0
    elif len(cleaned) == 11 and cleaned.startswith("0"):
        cleaned = cleaned[1:]

    # Step 4: Validate exactly 10 digits
    if len(cleaned) != 10 or not cleaned.isdigit():
        return (
            False,
            cleaned,
            f"Phone number must be exactly 10 digits. We received {len(cleaned)} digits: '{cleaned}'.",
        )

    # Optional Indian mobile sanity check: starts with 6, 7, 8, or 9
    if cleaned[0] not in {"6", "7", "8", "9"}:
        return (
            False,
            cleaned,
            f"Invalid Indian mobile number '{cleaned}'. Standard mobile numbers begin with 6, 7, 8, or 9.",
        )

    return True, cleaned, ""


def format_phone_for_speech(phone: str) -> str:
    """Formats a 10-digit phone number in grouped digits for clear text-to-speech pronunciation."""
    if len(phone) == 10:
        return f"{' '.join(phone[:5])}, {' '.join(phone[5:])}"
    return " ".join(list(phone))


def mask_phone_number(phone: str) -> str:
    """Masks phone number showing only the last 4 digits for privacy."""
    if len(phone) >= 4:
        return "•" * (len(phone) - 4) + phone[-4:]
    return phone
