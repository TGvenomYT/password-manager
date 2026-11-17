"""`python -m password_manager erase`: what the uninstallers run, when asked to erase everything,
before they delete the app's folders. It removes what doesn't live in those folders:

  - the email alerts' app password, from the system password store
  - the vault database and its MySQL user (needs MySQL admin rights, like setup does)

It deletes no files; the uninstall script does that afterwards.
"""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional

import mysql.connector

from . import alerts
from . import config as cfgmod
from . import prefs as prefsmod
from .setup_cli import SetupError, _run_via_command, _run_via_connector, say


def drop_sql(database: str, user: str) -> List[str]:
    cfgmod.validate_identifier(database, "database name")
    cfgmod.validate_identifier(user, "database user")
    return [f"DROP DATABASE IF EXISTS `{database}`", f"DROP USER IF EXISTS '{user}'@'localhost'"]


def forget_alerts() -> bool:
    address = prefsmod.load().alert_email
    if not address:
        return True
    result = alerts.forget_password(address)
    if result == "removed":
        say(f"Removed the app password for email alerts ({address}) from this computer's password store.")
    elif result == "failed":
        say(f"Couldn't remove the app password for email alerts ({address}) from this computer's password store.")
        say("Remove it yourself: it's saved as \"Password Manager email alerts\" (Keychain Access on macOS,")
        say("Credential Manager on Windows, Passwords and Keys on Linux).")
    return result != "failed"


def drop_database(args: argparse.Namespace) -> bool:
    """Drop the vault database and its MySQL user. False if it couldn't, after saying how to do it by hand."""
    path = cfgmod.config_path()
    if not path.exists():
        say("No database settings found, so there's no vault database to remove.")
        return True
    try:
        dbc = cfgmod.load(path).db
    except cfgmod.ConfigError as exc:
        say(f"Couldn't read {path}: {exc}")
        return False
    statements = drop_sql(dbc.database, dbc.user)
    try:
        done = bool(args.admin_command) and _run_via_command(args.admin_command, statements,
                                                             "Removing the vault database")
        if not done:
            _run_via_connector(dbc, args.admin_user, statements, offer_password=False)
    except (SetupError, mysql.connector.Error) as exc:
        say(f"Couldn't remove the vault database: {exc}")
        say("To remove it yourself, run this in MySQL as an admin (for example `sudo mysql` or `mysql -u root -p`):")
        for statement in statements:
            say(f"    {statement};")
        return False
    say(f"Removed the vault database '{dbc.database}' and MySQL user '{dbc.user}'.")
    return True


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="password_manager erase",
                                     description="Erase the vault database and the email alerts' app password.")
    parser.add_argument("--keep-database", action="store_true",
                        help="leave the database alone (Windows removes its private MySQL server instead)")
    parser.add_argument("--admin-user", default="root")
    parser.add_argument("--admin-command", default=None,
                        help='command that runs SQL as an admin from stdin, e.g. "sudo mysql" (tried first)')
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        ok = forget_alerts()
        ok = (True if args.keep_database else drop_database(args)) and ok
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        return 130
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
