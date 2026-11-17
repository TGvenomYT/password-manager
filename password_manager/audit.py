"""Password strength and reuse checks for the Security section. Everything runs locally."""

from __future__ import annotations

import math
import re
from collections import defaultdict
from typing import Dict, Iterable, List

LABELS = ["Very weak", "Weak", "Fair", "Good", "Strong"]

# The most common leaked passwords; any of these is "very weak" whatever its length.
COMMON = set("""
123456 123456789 12345678 password qwerty123 qwerty 1q2w3e4r 12345 111111 123123 1234567890
1234567 password1 abc123 000000 iloveyou 1234 qwertyuiop 123321 654321 666666 987654321 123qwe
dragon sunshine princess letmein monkey football baseball welcome admin login master hello
freedom whatever trustno1 shadow superman michael charlie password123 passw0rd zaq12wsx
asdfghjkl 112233 121212 qwe123 aa123456 1qaz2wsx 7777777 555555 696969 batman starwars
""".split())

_SEQUENCES = ("abcdefghijklmnopqrstuvwxyz", "qwertyuiopasdfghjklzxcvbnm", "01234567890")


def strength(password: str) -> int:
    """0 (very weak) to 4 (strong), from length, character variety and obvious patterns."""
    if not password:
        return 0
    if password.lower() in COMMON or len(password) < 6:
        return 0
    pool = 0
    pool += 26 if re.search(r"[a-z]", password) else 0
    pool += 26 if re.search(r"[A-Z]", password) else 0
    pool += 10 if re.search(r"[0-9]", password) else 0
    pool += 33 if re.search(r"[^a-zA-Z0-9]", password) else 0
    bits = len(password) * math.log2(max(pool, 2))
    if len(set(password)) <= max(2, len(password) // 4):
        bits /= 2  # "aaaaaaaa", "abababab"
    lowered = password.lower()
    if any(lowered[i:i + 4] in seq for seq in _SEQUENCES for i in range(len(lowered) - 3)):
        bits -= 15  # "1234", "abcd", "qwer"
    for limit, score in ((35, 0), (50, 1), (65, 2), (85, 3)):
        if bits < limit:
            return score
    return 4


def label(password: str) -> str:
    return LABELS[strength(password)]


def is_weak(password: str) -> bool:
    return bool(password) and strength(password) <= 1


def reused(entries: Iterable) -> Dict[int, List[int]]:
    """{entry id: ids of the *other* entries with the same password}, only for reused passwords."""
    by_password: Dict[str, List[int]] = defaultdict(list)
    for entry in entries:
        if entry.password:
            by_password[entry.password].append(entry.id)
    result: Dict[int, List[int]] = {}
    for ids in by_password.values():
        if len(ids) > 1:
            for entry_id in ids:
                result[entry_id] = [other for other in ids if other != entry_id]
    return result
