"""Where the app keeps its files, and the JSON config written by `setup`."""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

CONFIG_FILENAME = "config.json"
CREDENTIAL_FILENAME = "db-credential.gpg"

# Database and user names are interpolated into DDL, so they must be plain identifiers.
_IDENTIFIER = re.compile(r"^[A-Za-z0-9_]{1,64}$")


class ConfigError(Exception):
    """The config file is missing or invalid."""


def config_dir() -> Path:
    """Per-user directory for config.json and the GPG-encrypted DB credential."""
    override = os.environ.get("PASSWORD_MANAGER_HOME")
    if override:
        return Path(override).expanduser()
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming") / "PasswordManager"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "PasswordManager"
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "password-manager"


def validate_identifier(value: str, what: str) -> str:
    if not _IDENTIFIER.match(value):
        raise ConfigError(f"Invalid {what} {value!r}: use letters, digits and underscores only.")
    return value


@dataclass
class DbConfig:
    host: str = "localhost"
    port: int = 3306
    user: str = "pm_app"
    database: str = "password_manager"
    unix_socket: Optional[str] = None

    def __post_init__(self) -> None:
        validate_identifier(self.user, "database user")
        validate_identifier(self.database, "database name")
        self.port = int(self.port)


@dataclass
class Config:
    db: DbConfig = field(default_factory=DbConfig)
    # Relative paths are resolved against config_dir().
    credential_file: str = CREDENTIAL_FILENAME
    # Absolute path to gpg, recorded at setup so launchers with a minimal PATH still find it.
    gpg_binary: Optional[str] = None

    def credential_path(self) -> Path:
        path = Path(self.credential_file).expanduser()
        return path if path.is_absolute() else config_dir() / path


def config_path() -> Path:
    return config_dir() / CONFIG_FILENAME


def load(path: Optional[Path] = None) -> Config:
    path = path or config_path()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ConfigError(f"Not configured yet ({path} is missing).") from None
    except (OSError, ValueError) as exc:
        raise ConfigError(f"Could not read {path}: {exc}") from exc
    try:
        return Config(
            db=DbConfig(**raw.get("db", {})),
            credential_file=raw.get("credential_file", CREDENTIAL_FILENAME),
            gpg_binary=raw.get("gpg_binary"),
        )
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"Invalid config in {path}: {exc}") from exc


def save(cfg: Config, path: Optional[Path] = None) -> Path:
    """Write the config atomically with owner-only permissions."""
    path = path or config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path.parent, 0o700)
    except OSError:
        pass
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".config-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(asdict(cfg), fh, indent=2)
            fh.write("\n")
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return path
