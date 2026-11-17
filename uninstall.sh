#!/usr/bin/env bash
# Password Manager MARK IV: uninstall on macOS and Linux.
#
#   ./uninstall.sh         Remove the app and its launcher. Your vault and settings are kept,
#                          so running install.sh again picks up where you left off.
#   ./uninstall.sh --all   Also erase your vault (every saved password), its MySQL user, your
#                          settings and the email alerts' app password. Asks you to type ERASE.
#
# Without cloning:
#   curl -fsSL https://raw.githubusercontent.com/TGvenomYT/password-manager/main/uninstall.sh | bash
#   curl -fsSL https://raw.githubusercontent.com/TGvenomYT/password-manager/main/uninstall.sh | bash -s -- --all
#
# Python, GnuPG and MySQL stay installed: other programs may use them.

set -euo pipefail

APP_NAME="Password Manager"

info() { printf '\033[1;36m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33mWarning:\033[0m %s\n' "$*" >&2; }
die() { printf '\033[1;31mError:\033[0m %s\n' "$*" >&2; exit 1; }
usage() { sed -n '2,13p' "${BASH_SOURCE[0]:-}" 2>/dev/null | sed 's/^# \{0,1\}//' || true; }
have() { command -v "$1" >/dev/null 2>&1; }

# Piped from curl, this script *is* stdin, so the ERASE answer has to come from the terminal.
ask() {
    local reply=""
    if [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
        read -r -p "$1" reply || true
    elif (exec </dev/tty) 2>/dev/null; then
        read -r -p "$1" reply </dev/tty || true
    fi
    printf '%s' "$reply"
}

ALL=0
for arg in "$@"; do
    case "$arg" in
        --all) ALL=1 ;;
        -h|--help) usage; exit 0 ;;
        *) die "Unknown option: $arg (see --help)" ;;
    esac
done

OS="$(uname -s)"
case "$OS" in
    Darwin)
        CONFIG_DIR="$HOME/Library/Application Support/PasswordManager"
        INSTALL_DIR="$CONFIG_DIR/app"
        DATA_DIR=""
        LAUNCHERS=("$HOME/Applications/$APP_NAME.app")
        APP_BINARY="$HOME/Applications/$APP_NAME.app/Contents/MacOS/PasswordManager"
        ;;
    Linux)
        CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/password-manager"
        DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/password-manager"
        INSTALL_DIR="$DATA_DIR/app"
        LAUNCHERS=("${XDG_DATA_HOME:-$HOME/.local/share}/applications/password-manager.desktop"
                   "$HOME/.local/bin/password-manager")
        APP_BINARY="$INSTALL_DIR/bin/PasswordManager"
        ;;
    *) die "Unsupported system: $OS. On Windows, run uninstall.bat." ;;
esac

if [ "$ALL" -eq 1 ]; then
    echo
    echo "This erases your vault: every saved password, your master password and recovery key,"
    echo "your settings and GPG-protected database login, the vault's MySQL database and user,"
    echo "and the email alerts' app password. It cannot be undone."
    echo
    answer="$(ask "Type ERASE to continue, or press Enter to cancel: ")"
    echo
    if [ "$answer" != "ERASE" ]; then
        echo "Cancelled. Nothing was removed."
        exit 0
    fi
fi

info "Closing $APP_NAME if it is open..."
pkill -f "$INSTALL_DIR/" 2>/dev/null || true
[ "$OS" = Darwin ] && { pkill -f "$APP_BINARY" 2>/dev/null || true; }

# config.json (written by setup) says which database, user and server the vault uses.
config_value() {
    sed -n "s/^ *\"$1\": *\"\{0,1\}\([^\",]*\)\"\{0,1\},\{0,1\}\$/\1/p" "$CONFIG_DIR/config.json" 2>/dev/null | head -n 1
}

# Used when the app is already gone (e.g. after a plain uninstall): drop the database with the mysql client.
drop_with_mysql_client() {
    local database user host port socket sql
    database="$(config_value database)"; user="$(config_value user)"
    host="$(config_value host)"; port="$(config_value port)"; socket="$(config_value unix_socket)"
    database="${database:-password_manager}"; user="${user:-pm_app}"
    case "$database$user" in *[!A-Za-z0-9_]*) warn "Unexpected database or user name in config.json."; return 1 ;; esac
    sql="DROP DATABASE IF EXISTS \`$database\`; DROP USER IF EXISTS '$user'@'localhost';"
    local target=()
    if [ -n "$socket" ] && [ "$socket" != null ]; then target=(--socket="$socket")
    else target=(-h "${host:-localhost}" -P "${port:-3306}"); fi
    [ "${host:-localhost}" = localhost ] && [ "${#target[@]}" -gt 1 ] && target=(-h 127.0.0.1 -P "${port:-3306}")
    if have mysql; then
        if [ "$OS" = Linux ] && [ "$(id -u)" -ne 0 ] && have sudo && sudo mysql -e "$sql" 2>/dev/null; then return 0; fi
        if mysql -u root "${target[@]}" -e "$sql" 2>/dev/null; then return 0; fi
        echo "    MySQL's root account needs its password:"
        if mysql -u root -p "${target[@]}" -e "$sql"; then return 0; fi
    fi
    warn "Couldn't remove the vault database. Run this in MySQL as an admin (sudo mysql, or mysql -u root -p):"
    echo "        $sql"
    return 1
}

FAILED=0
if [ "$ALL" -eq 1 ]; then
    # The app itself erases what isn't a file, while its settings still say where things are.
    erase=()
    if [ -x "$APP_BINARY" ]; then
        erase=("$APP_BINARY" erase)
    elif [ -x "$INSTALL_DIR/venv/bin/python" ]; then
        erase=("$INSTALL_DIR/venv/bin/python" -m password_manager erase)
    fi
    if [ "$OS" = Linux ]; then
        # Ubuntu/Debian MySQL and MariaDB let the OS root user in via unix_socket, as setup did.
        if [ "$(id -u)" -eq 0 ]; then erase+=(--admin-command "mysql")
        elif have sudo; then erase+=(--admin-command "sudo mysql"); fi
    fi
    if [ "${#erase[@]}" -gt 1 ] && [ -x "${erase[0]}" ]; then
        info "Removing the vault database and the email alerts' app password..."
        [ "$OS" = Darwin ] && echo "    (macOS may ask to let $APP_NAME use your Keychain: choose Allow.)"
        "${erase[@]}" || FAILED=1
    elif [ -f "$CONFIG_DIR/config.json" ]; then
        info "Removing the vault database..."
        if drop_with_mysql_client; then echo "    Removed the vault database and its MySQL user."; else FAILED=1; fi
    else
        echo "    No settings found, so there's no vault database to remove."
    fi
fi

info "Removing the app..."
for launcher in "${LAUNCHERS[@]}"; do
    if [ -e "$launcher" ] || [ -L "$launcher" ]; then rm -rf "$launcher"; echo "    Removed $launcher"; fi
done
if [ -d "$INSTALL_DIR" ]; then rm -rf "${INSTALL_DIR:?}"; echo "    Removed $INSTALL_DIR"; fi

if [ "$ALL" -eq 0 ]; then
    echo
    info "Done. Your vault and settings were kept:"
    echo "    - MySQL database 'password_manager' and MySQL user 'pm_app'"
    echo "    - settings and GPG-protected database login in: $CONFIG_DIR"
    echo "Run install.sh to install again. To erase everything instead, run:  ./uninstall.sh --all"
    exit 0
fi

info "Removing your settings..."
for dir in "$CONFIG_DIR" "$DATA_DIR"; do
    if [ -n "$dir" ] && [ -d "$dir" ]; then rm -rf "${dir:?}"; echo "    Removed $dir"; fi
done

echo
if [ "$FAILED" -eq 0 ]; then
    info "Done. Everything was erased."
else
    warn "Done, except for the steps above that need finishing by hand."
fi
echo "Python, GnuPG and MySQL are still installed; remove them yourself if nothing else uses them."
exit "$FAILED"
