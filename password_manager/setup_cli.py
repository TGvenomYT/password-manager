"""`python -m password_manager setup`: first-time configuration, run by the installers.

1. Wait for the local MySQL/MariaDB server.
2. Using an admin account (root, or `sudo mysql` on Linux), create the
   database and a dedicated least-privilege user with a random password. The
   app no longer connects as root.
3. GPG-encrypt that password with a passphrase the user chooses.
4. Write config.json.

The vault itself (master password) is set up by the GUI on first launch.
"""

from __future__ import annotations

import argparse
import getpass
import secrets
import shlex
import socket
import subprocess
import sys
import time
from typing import List, Optional

import mysql.connector
from mysql.connector import errorcode

from . import config as cfgmod
from . import credentials, db
from .vault import Vault

MIN_PASSPHRASE_LENGTH = 8


class SetupError(Exception):
    pass


def say(message: str = "") -> None:
    print(message, flush=True)


def ask_yes_no(question: str, default: bool = True) -> bool:
    suffix = " [Y/n] " if default else " [y/N] "
    while True:
        try:
            answer = input(question + suffix).strip().lower()
        except EOFError:
            return default
        if not answer:
            return default
        if answer in ("y", "yes", "n", "no"):
            return answer.startswith("y")


def ask_new_secret(label: str, minimum: int) -> str:
    while True:
        first = getpass.getpass(f"{label}: ")
        if len(first) < minimum:
            say(f"  Must be at least {minimum} characters.")
            continue
        if getpass.getpass(f"{label} (again): ") != first:
            say("  They don't match. Try again.")
            continue
        return first


def provisioning_sql(database: str, user: str, password: str) -> List[str]:
    cfgmod.validate_identifier(database, "database name")
    cfgmod.validate_identifier(user, "database user")
    if not all(c.isalnum() or c in "-_" for c in password):
        raise ValueError("generated password must be URL-safe")
    return [
        f"CREATE DATABASE IF NOT EXISTS `{database}` CHARACTER SET utf8mb4",
        f"CREATE USER IF NOT EXISTS '{user}'@'localhost' IDENTIFIED BY '{password}'",
        f"ALTER USER '{user}'@'localhost' IDENTIFIED BY '{password}'",
        f"GRANT ALL PRIVILEGES ON `{database}`.* TO '{user}'@'localhost'",
    ]


def wait_for_server(dbc: cfgmod.DbConfig, timeout: float) -> None:
    if dbc.unix_socket:
        return
    deadline = time.monotonic() + timeout
    announced = False
    while True:
        try:
            with socket.create_connection((dbc.host, dbc.port), timeout=2):
                return
        except OSError:
            if time.monotonic() >= deadline:
                raise SetupError(
                    f"MySQL is not reachable on {dbc.host}:{dbc.port}. Is the server running?"
                ) from None
            if not announced:
                say(f"Waiting for MySQL on {dbc.host}:{dbc.port}...")
                announced = True
            time.sleep(1)


def _admin_connect(dbc: cfgmod.DbConfig, user: str, password: str):
    kwargs = dict(user=user, password=password, connection_timeout=10)
    if dbc.unix_socket:
        kwargs["unix_socket"] = dbc.unix_socket
    else:
        kwargs.update(host=dbc.host, port=dbc.port)
    return mysql.connector.connect(**kwargs)


def _run_via_command(command: str, statements: List[str]) -> bool:
    script = ";\n".join(statements) + ";\n"
    say(f"Creating the database user with: {command}")
    try:
        proc = subprocess.run(shlex.split(command), input=script.encode(), capture_output=True, timeout=300)
    except (OSError, subprocess.TimeoutExpired) as exc:
        say(f"  That didn't work ({exc}).")
        return False
    if proc.returncode != 0:
        say(f"  That didn't work: {proc.stderr.decode(errors='replace').strip()}")
        return False
    return True


def _run_via_connector(dbc: cfgmod.DbConfig, admin_user: str, statements: List[str]) -> None:
    conn = None
    try:
        conn = _admin_connect(dbc, admin_user, "")
        say(f"Connected to MySQL as '{admin_user}', which has NO password.")
        say("Any program on this computer can currently read or delete every database.")
        if ask_yes_no(f"Set a password for the MySQL '{admin_user}' account now? (recommended)"):
            new = ask_new_secret(f"New MySQL {admin_user} password", 8)
            cur = conn.cursor()
            cur.execute("ALTER USER CURRENT_USER() IDENTIFIED BY %s", (new,))
            cur.close()
            say(f"  MySQL '{admin_user}' password set. Keep it safe; the app doesn't need it.")
    except mysql.connector.Error as exc:
        if exc.errno not in (errorcode.ER_ACCESS_DENIED_ERROR, errorcode.ER_NOT_SUPPORTED_AUTH_MODE, 1698):
            raise SetupError(f"Could not connect to MySQL: {exc}") from exc
        for attempt in range(3):
            password = getpass.getpass(f"MySQL '{admin_user}' password: ")
            try:
                conn = _admin_connect(dbc, admin_user, password)
                break
            except mysql.connector.Error as inner:
                if inner.errno != errorcode.ER_ACCESS_DENIED_ERROR:
                    raise SetupError(f"Could not connect to MySQL: {inner}") from inner
                say("  Access denied.")
        else:
            raise SetupError(f"Could not log in to MySQL as '{admin_user}'.") from None
    try:
        cur = conn.cursor()
        for statement in statements:
            cur.execute(statement)
        conn.commit()
        cur.close()
    finally:
        conn.close()


def run_setup(args: argparse.Namespace) -> int:
    path = cfgmod.config_path()
    if not args.reconfigure and path.exists():
        try:
            existing = cfgmod.load(path)
            if existing.credential_path().is_file():
                say(f"Already configured ({path}). Use --reconfigure to start over.")
                return 0
        except cfgmod.ConfigError:
            pass  # broken config, so set up again

    dbc = cfgmod.DbConfig(
        host=args.host, port=args.port, user=args.app_user, database=args.database, unix_socket=args.socket
    )
    gpg = credentials.find_gpg()
    wait_for_server(dbc, args.wait)

    app_password = secrets.token_urlsafe(24)
    statements = provisioning_sql(dbc.database, dbc.user, app_password)
    done = bool(args.admin_command) and _run_via_command(args.admin_command, statements)
    if not done:
        _run_via_connector(dbc, args.admin_user, statements)
    say(f"Database '{dbc.database}' and MySQL user '{dbc.user}'@'localhost' are ready.")

    say("")
    say("Choose a GPG passphrase. It encrypts the database password on disk, and the app")
    say("asks for it at launch (gpg-agent usually remembers it for a few minutes).")
    say("This is separate from your master password, which you set in the app.")
    passphrase = ask_new_secret("GPG passphrase", MIN_PASSPHRASE_LENGTH)

    cfg = cfgmod.Config(db=dbc, gpg_binary=gpg)
    cred_path = cfg.credential_path()
    credentials.encrypt_secret(app_password, passphrase, cred_path, gpg)
    if credentials.decrypt_with_passphrase(cred_path, passphrase, gpg, cache=False) != app_password:
        raise SetupError("GPG round-trip check failed.")

    conn = db.connect(dbc, app_password)
    try:
        Vault(conn).ensure_schema()
    finally:
        conn.close()
    cfgmod.save(cfg, path)
    say(f"Saved configuration to {path}")
    say("Setup complete. Open Password Manager to create (or unlock) your vault.")
    return 0


def build_parser(parser: Optional[argparse.ArgumentParser] = None) -> argparse.ArgumentParser:
    parser = parser or argparse.ArgumentParser(prog="password_manager setup")
    parser.add_argument("--reconfigure", action="store_true", help="redo setup even if already configured")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=3306)
    parser.add_argument("--socket", default=None, help="connect through this Unix socket instead of TCP")
    parser.add_argument("--database", default="password_manager")
    parser.add_argument("--app-user", default="pm_app", help="MySQL user the app connects as")
    parser.add_argument("--admin-user", default="root")
    parser.add_argument(
        "--admin-command",
        default=None,
        help='command that runs SQL as an admin from stdin, e.g. "sudo mysql" (tried first)',
    )
    parser.add_argument("--wait", type=float, default=60, help="seconds to wait for MySQL to start")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return run_setup(args)
    except (SetupError, credentials.GpgError, cfgmod.ConfigError, mysql.connector.Error) as exc:
        print(f"Setup failed: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nSetup cancelled.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
