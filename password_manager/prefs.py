"""Per-user preferences (nothing secret), stored as preferences.json next to config.json."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, fields

from . import config as cfgmod

log = logging.getLogger(__name__)


@dataclass
class Prefs:
    auto_lock_minutes: int = 5     # 0 = never
    clipboard_seconds: int = 30    # 0 = never clear
    generator_style: str = "random"
    generator_length: int = 20
    generator_digits: bool = True
    generator_symbols: bool = True
    reduce_motion: bool = False     # calmer interface: no liquid background or springy motion
    theme: str = "aurora"           # colour theme: aurora, ocean, sunset, forest
    sort: str = "name"              # list order: name, modified, created
    alert_email: str = ""           # email alerts go from this address to itself; its app password is in the keyring
    email_alerts: bool = False


def _path():
    return cfgmod.config_dir() / "preferences.json"


def load() -> Prefs:
    try:
        data = json.loads(_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return Prefs()
    prefs = Prefs()
    for field in fields(Prefs):
        value = data.get(field.name)
        if isinstance(value, type(getattr(prefs, field.name))):
            setattr(prefs, field.name, value)
    if prefs.generator_style not in ("random", "memorable"):
        prefs.generator_style = "random"
    if prefs.theme not in ("aurora", "ocean", "sunset", "forest"):
        prefs.theme = "aurora"
    if prefs.sort not in ("name", "modified", "created"):
        prefs.sort = "name"
    return prefs


def save(prefs: Prefs) -> None:
    try:
        path = _path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(prefs), indent=2), encoding="utf-8")
    except OSError:
        log.warning("Could not save preferences.", exc_info=True)
