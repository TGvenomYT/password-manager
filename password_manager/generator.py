"""Password generator."""

from __future__ import annotations

import secrets

MIN_LENGTH = 8
MAX_LENGTH = 64
# No look-alikes (I l 1 O 0), and no quotes or backslashes, which break CSV files and shells.
LOWER = "abcdefghijkmnopqrstuvwxyz"
UPPER = "ABCDEFGHJKLMNPQRSTUVWXYZ"
DIGITS = "23456789"
SYMBOLS = "!#$%&*+-=?@^_~"
CONSONANTS = "bcdfghjkmnprstvwxz"
VOWELS = "aeiou"

_rng = secrets.SystemRandom()


def random_password(length: int = 20, *, digits: bool = True, symbols: bool = True) -> str:
    """Random characters, with at least one from every chosen group."""
    length = max(MIN_LENGTH, min(MAX_LENGTH, int(length)))
    groups = [LOWER, UPPER] + ([DIGITS] if digits else []) + ([SYMBOLS] if symbols else [])
    chars = [secrets.choice(group) for group in groups]
    pool = "".join(groups)
    chars += [secrets.choice(pool) for _ in range(length - len(chars))]
    _rng.shuffle(chars)
    return "".join(chars)


def memorable_password() -> str:
    """Three pronounceable groups like ``kabomi-Tefuna-ri7oke``: easy to type on a phone,
    about 65 bits of randomness."""
    groups = ["".join(secrets.choice(CONSONANTS if i % 2 == 0 else VOWELS) for i in range(6)) for _ in range(3)]
    flat = list("".join(groups))
    upper_at, digit_at = _rng.sample(range(len(flat)), 2)
    flat[upper_at] = flat[upper_at].upper()
    flat[digit_at] = secrets.choice(DIGITS)
    text = "".join(flat)
    return "-".join(text[i:i + 6] for i in (0, 6, 12))
