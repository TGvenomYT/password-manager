#!/bin/bash
# Password Manager MARK IV: double-click this file in Finder to uninstall on macOS.
# It removes the app and keeps your vault. To erase everything, run ./uninstall.sh --all in Terminal.
cd "$(dirname "$0")" || exit 1
bash ./uninstall.sh "$@"
status=$?
echo
read -r -p "Press Return to close this window..." _
exit "$status"
