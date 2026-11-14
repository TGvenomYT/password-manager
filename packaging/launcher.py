"""Entry script for PyInstaller builds (PyInstaller needs a script file, not `python -m`)."""

import sys

from password_manager.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
