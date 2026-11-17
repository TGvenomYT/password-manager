"""Import passwords from other managers' CSV exports, and export to CSV."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, Iterable, List

# Column names used by Chrome, Edge, Safari, Firefox, Bitwarden, 1Password, LastPass and others.
ALIASES = {
    "title": ("title", "name", "account", "item name", "login_name"),
    "website": ("url", "website", "login_uri", "uri", "web site", "login url", "hostname"),
    "username": ("username", "user name", "login_username", "login", "user", "email", "e-mail"),
    "password": ("password", "login_password", "pass"),
    "notes": ("notes", "note", "extra", "comments", "comment"),
    "totp": ("totp", "otpauth", "login_totp", "otp", "2fa", "one-time password"),
}
EXPORT_HEADER = ["name", "url", "username", "password", "note"]  # Chrome's format, which most apps import


def read_csv(path) -> List[Dict[str, str]]:
    """Rows as {title, website, username, password, notes}. Rows without a password are skipped."""
    with open(path, newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("The file is empty.")
        columns = {name.strip().lower(): name for name in reader.fieldnames if name}
        mapping = {}
        for field, names in ALIASES.items():
            found = next((columns[n] for n in names if n in columns), None)
            if found:
                mapping[field] = found
        if "password" not in mapping:
            raise ValueError("This file has no password column. Export a CSV of your passwords from the "
                             "other app and try again.")
        rows = []
        for row in reader:
            item = {field: (row.get(column) or "").strip() if field != "password" else (row.get(column) or "")
                    for field, column in mapping.items()}
            if item.get("password"):
                rows.append({key: item.get(key, "") for key in ALIASES})
        return rows


def write_csv(path, entries: Iterable) -> int:
    count = 0
    with open(Path(path), "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(EXPORT_HEADER)
        for entry in entries:
            if entry.password is None:
                continue
            writer.writerow([entry.name, entry.website, entry.username, entry.password, entry.notes])
            count += 1
    return count
