#!/bin/bash
# Password Manager MARK IV: double-click this file in Finder to install on macOS.
cd "$(dirname "$0")" || exit 1
bash ./install.sh "$@"
status=$?
echo
read -r -p "Press Return to close this window..." _
exit "$status"
