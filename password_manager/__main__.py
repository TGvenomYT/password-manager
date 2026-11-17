"""Entry point.

    python -m password_manager            launch the app
    python -m password_manager setup      first-time configuration (run by the installers)
    python -m password_manager erase      remove the vault database and the email alerts' app password
                                          (run by the uninstallers when erasing everything)
    python -m password_manager --version
"""

from __future__ import annotations

import logging
import logging.handlers
import sys
from typing import List, Optional

from . import __version__
from .config import config_dir


def _configure_logging() -> None:
    # Windowed builds (e.g. PasswordManager.exe) have no stderr at all.
    handlers: List[logging.Handler] = [logging.StreamHandler()] if sys.stderr else []
    try:
        log_dir = config_dir()
        log_dir.mkdir(parents=True, exist_ok=True)
        handlers.append(
            logging.handlers.RotatingFileHandler(
                log_dir / "password-manager.log", maxBytes=512_000, backupCount=2, encoding="utf-8"
            )
        )
    except OSError:
        pass
    # Never log secrets: only events and errors are logged.
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s",
                        handlers=handlers)


def self_test() -> int:
    """Check that every runtime piece loads. The installers run this on a freshly built binary."""
    import importlib

    from . import crypto
    from .app import ICON_FILES, MAIN_QML, self_test_ui

    # The connector loads its auth plugins dynamically, so check that the build bundled them.
    for module in ("bcrypt", "mysql.connector", "mysql.connector.plugins.caching_sha2_password",
                   "mysql.connector.plugins.mysql_native_password", "PySide6.QtQuick", "PySide6.QtQml"):
        importlib.import_module(module)
    crypto.derive_kek("self-test", crypto.KdfParams(salt=b"\0" * 16, n=2**10))
    for path in (*ICON_FILES, MAIN_QML):
        if not path.is_file():
            raise RuntimeError(f"missing file: {path}")
    import ssl

    import certifi
    ssl.create_default_context(cafile=certifi.where())  # the leak check's certificate list is bundled and valid
    import keyring  # email alerts keep their app password in the system password store

    from . import alerts  # noqa: F401
    backend = keyring.get_keyring()
    if sys.platform in ("darwin", "win32") and type(backend).__module__.startswith("keyring.backends.fail"):
        raise RuntimeError("no system password store backend was bundled")
    problems = self_test_ui()
    if problems:
        raise RuntimeError("the interface didn't load:\n" + "\n".join(problems))
    print(f"Password Manager {__version__}: self-test OK")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] in (["--version"], ["-V"]):
        print(f"Password Manager {__version__}")
        return 0
    if argv[:1] == ["--self-test"]:
        return self_test()
    if argv[:1] in (["-h"], ["--help"]):
        print(__doc__.strip())
        return 0
    _configure_logging()
    if argv[:1] == ["setup"]:
        from .setup_cli import main as setup_main

        return setup_main(argv[1:])
    if argv[:1] == ["erase"]:
        from .erase_cli import main as erase_main

        return erase_main(argv[1:])
    if argv:
        print(f"Unknown arguments: {' '.join(argv)}\n\n{__doc__.strip()}", file=sys.stderr)
        return 2
    from .app import main as app_main

    return app_main()


if __name__ == "__main__":
    sys.exit(main())
