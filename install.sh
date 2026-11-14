#!/usr/bin/env bash
# Password Manager MARK IV: one-step installer for macOS and Linux.
#
#   ./install.sh                 install or upgrade, then launch the app
#   ./install.sh --reconfigure   redo the database user + GPG credential setup
#   ./install.sh --uninstall     remove the app (keeps your vault, config and MySQL)
#   ./install.sh --no-launch     don't open the app at the end
#   PM_SETUP_ARGS="--port 3307"  extra options for `password_manager setup` (custom port, socket, ...)
#
# Remote install, without cloning:
#   curl -fsSL https://raw.githubusercontent.com/TGvenomYT/password-manager/main/install.sh | bash
#
# What it does: installs Python 3 with Tkinter, GnuPG and MySQL (Homebrew on macOS;
# apt, dnf or pacman on Linux), starts MySQL, installs the app into its own
# virtualenv, runs the guided setup, and adds an app launcher.

set -euo pipefail

REPO_TARBALL="${PM_SOURCE_URL:-https://github.com/TGvenomYT/password-manager/archive/refs/heads/main.tar.gz}"
APP_NAME="Password Manager"
BUNDLE_ID="io.github.tgvenomyt.passwordmanager"

info() { printf '\033[1;36m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33mWarning:\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31mError:\033[0m %s\n' "$*" >&2; exit 1; }

usage() { sed -n '2,15p' "$0" 2>/dev/null | sed 's/^# \{0,1\}//'; }

have() { command -v "$1" >/dev/null 2>&1; }

# Returns success if /dev/tty can be opened (false under CI or a detached session).
have_tty() { (exec </dev/tty) 2>/dev/null; }

db_port_open() { (exec 3<>/dev/tcp/127.0.0.1/3306) 2>/dev/null; }

have_mysql_server() {
    have mysqld || have mariadbd || [ -x /usr/sbin/mysqld ] || [ -x /usr/sbin/mariadbd ] || db_port_open
}

# A Python >= 3.9 whose tkinter works with Tk >= 8.6 (the macOS system Python ships Tk 8.5, which is broken).
find_python() {
    local candidate
    for candidate in python3.13 python3.12 python3.11 python3.10 python3.14 python3.9 python3 \
                     /opt/homebrew/bin/python3.13 /usr/local/bin/python3.13; do
        have "$candidate" || continue
        if "$candidate" -c 'import sys, tkinter; sys.exit(0 if sys.version_info >= (3, 9) and tkinter.TkVersion >= 8.6 else 1)' \
            >/dev/null 2>&1; then
            command -v "$candidate"
            return 0
        fi
    done
    return 1
}

# --------------------------------------------------------------------------- macOS

mac_ensure_brew() {
    if ! have brew; then
        local b
        for b in /opt/homebrew/bin/brew /usr/local/bin/brew; do
            if [ -x "$b" ]; then eval "$("$b" shellenv)"; break; fi
        done
    fi
    if ! have brew; then
        info "Installing Homebrew (it will ask for your Mac password)..."
        have_tty || die "Homebrew must be installed interactively. Run this installer from Terminal."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" </dev/tty
        local b
        for b in /opt/homebrew/bin/brew /usr/local/bin/brew; do
            if [ -x "$b" ]; then eval "$("$b" shellenv)"; break; fi
        done
        have brew || die "Homebrew installation failed."
    fi
}

mac_deps() {
    mac_ensure_brew
    export HOMEBREW_NO_INSTALL_CLEANUP=1 HOMEBREW_NO_ENV_HINTS=1
    local want=()
    have gpg || want+=(gnupg)
    have_mysql_server || want+=(mysql)
    PY="$(find_python || true)"
    [ -n "$PY" ] || want+=(python-tk@3.13)
    if [ "${#want[@]}" -gt 0 ]; then
        info "Installing with Homebrew: ${want[*]}"
        brew install "${want[@]}" </dev/null
    fi
    [ -n "$PY" ] || PY="$(find_python)" || die "Could not find a Python with Tkinter after installing python-tk."

    if ! db_port_open; then
        local formula
        formula="$(brew list --formula 2>/dev/null | grep -E '^(mysql|mariadb)(@[0-9.]+)?$' | head -n 1 || true)"
        if [ -n "$formula" ]; then
            info "Starting $formula..."
            brew services start "$formula" </dev/null
        else
            warn "MySQL is installed but not running, and it isn't a Homebrew service. Start it yourself."
        fi
    fi
}

mac_launcher() {
    local app="$HOME/Applications/$APP_NAME.app"
    if [ -e "$app" ] && ! grep -q "$BUNDLE_ID" "$app/Contents/Info.plist" 2>/dev/null; then
        die "$app already exists and isn't ours; not touching it."
    fi
    rm -rf "$app"
    mkdir -p "$app/Contents/MacOS"
    cat >"$app/Contents/MacOS/PasswordManager" <<EOF
#!/bin/bash
exec "$VENV/bin/python" -m password_manager "\$@"
EOF
    chmod 755 "$app/Contents/MacOS/PasswordManager"
    cat >"$app/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key><string>$APP_NAME</string>
    <key>CFBundleDisplayName</key><string>$APP_NAME</string>
    <key>CFBundleIdentifier</key><string>$BUNDLE_ID</string>
    <key>CFBundleExecutable</key><string>PasswordManager</string>
    <key>CFBundlePackageType</key><string>APPL</string>
    <key>CFBundleShortVersionString</key><string>$VERSION</string>
    <key>LSMinimumSystemVersion</key><string>11.0</string>
    <key>NSHighResolutionCapable</key><true/>
</dict>
</plist>
EOF
    LAUNCH_CMD=(open "$app")
    info "Added \"$APP_NAME\" to $HOME/Applications (also searchable in Spotlight)."
}

mac_uninstall_launcher() { rm -rf "$HOME/Applications/$APP_NAME.app"; }

# --------------------------------------------------------------------------- Linux

SUDO=()
linux_sudo() {
    if [ "$(id -u)" -eq 0 ]; then SUDO=(); return; fi
    have sudo || die "sudo is required to install system packages."
    SUDO=(sudo)
}

linux_deps() {
    linux_sudo
    local pkgs=()
    if have apt-get; then
        pkgs=(python3 python3-venv python3-tk gnupg)
        if ! have_mysql_server; then
            # Debian lists mysql-server as a purely virtual package (exit 0, no Version), so check for a real one.
            if apt-cache show mysql-server 2>/dev/null | grep -q '^Version:'; then pkgs+=(mysql-server); else pkgs+=(default-mysql-server); fi
        fi
        info "Installing with apt: ${pkgs[*]}"
        "${SUDO[@]}" apt-get update -qq </dev/null
        "${SUDO[@]}" env DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "${pkgs[@]}" </dev/null
    elif have dnf; then
        pkgs=(python3 python3-tkinter gnupg2)
        if ! have_mysql_server; then
            if dnf -q info mysql-server >/dev/null 2>&1; then pkgs+=(mysql-server)
            elif dnf -q info community-mysql-server >/dev/null 2>&1; then pkgs+=(community-mysql-server)
            else pkgs+=(mariadb-server); fi
        fi
        info "Installing with dnf: ${pkgs[*]}"
        "${SUDO[@]}" dnf install -y -q "${pkgs[@]}" </dev/null
    elif have pacman; then
        pkgs=(python tk gnupg)
        have_mysql_server || pkgs+=(mariadb)
        info "Installing with pacman: ${pkgs[*]}"
        "${SUDO[@]}" pacman -S --needed --noconfirm "${pkgs[@]}" </dev/null
        if [ ! -d /var/lib/mysql/mysql ] && have mariadb-install-db; then
            "${SUDO[@]}" mariadb-install-db --user=mysql --basedir=/usr --datadir=/var/lib/mysql >/dev/null
        fi
    else
        warn "Unknown package manager. Make sure Python 3.9+ with Tkinter, GnuPG and MySQL/MariaDB are installed."
    fi
    PY="$(find_python)" || die "No Python 3.9+ with Tkinter found."

    if ! db_port_open; then
        info "Starting the database server..."
        linux_start_db || warn "Could not start MySQL automatically. Start it, then re-run this installer."
    fi
}

wait_db() {
    local i
    for ((i = 0; i < $1; i++)); do db_port_open && return 0; sleep 1; done
    return 1
}

# Don't trust exit codes alone: systemctl can exit 0 inside containers where systemd isn't running.
linux_start_db() {
    local svc started
    for svc in mysql mariadb mysqld; do
        started=1
        if have systemctl && [ -d /run/systemd/system ]; then
            "${SUDO[@]}" systemctl enable --now "$svc" >/dev/null 2>&1 && started=0
        elif have service || [ -x /usr/sbin/service ] || [ -x /sbin/service ]; then  # sbin isn't on a normal user's PATH
            "${SUDO[@]}" service "$svc" start >/dev/null 2>&1 && started=0
        fi
        if [ "$started" -eq 0 ] && wait_db 30; then return 0; fi
    done
    return 1
}

linux_launcher() {
    local data="${XDG_DATA_HOME:-$HOME/.local/share}"
    local desktop="$data/applications/password-manager.desktop"
    mkdir -p "$data/applications" "$HOME/.local/bin"
    cat >"$desktop" <<EOF
[Desktop Entry]
Type=Application
Name=$APP_NAME
Comment=Local encrypted password vault
Exec="$VENV/bin/python" -m password_manager
Icon=dialog-password
Terminal=false
Categories=Utility;Security;
EOF
    chmod 644 "$desktop"
    have update-desktop-database && update-desktop-database "$data/applications" >/dev/null 2>&1 || true
    ln -sf "$VENV/bin/password-manager" "$HOME/.local/bin/password-manager"
    if [ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]; then
        LAUNCH_CMD=(nohup "$VENV/bin/python" -m password_manager)
    fi
    info "Added \"$APP_NAME\" to your applications menu, and the command ~/.local/bin/password-manager."
}

linux_uninstall_launcher() {
    rm -f "${XDG_DATA_HOME:-$HOME/.local/share}/applications/password-manager.desktop" "$HOME/.local/bin/password-manager"
}

# --------------------------------------------------------------------------- common

resolve_source() {
    local here=""
    if [ -n "${BASH_SOURCE[0]:-}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
        here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    fi
    if [ -n "$here" ] && [ -f "$here/pyproject.toml" ] && [ -d "$here/password_manager" ]; then
        SRC="$here"
        return
    fi
    have curl || die "curl is required to download the app."
    TMP_SRC="$(mktemp -d)"
    trap 'rm -rf "$TMP_SRC"' EXIT
    info "Downloading $REPO_TARBALL"
    curl -fsSL "$REPO_TARBALL" | tar -xz -C "$TMP_SRC" --strip-components 1
    SRC="$TMP_SRC"
}

install_app() {
    mkdir -p "$INSTALL_DIR"
    if [ -x "$VENV/bin/python" ] && ! "$VENV/bin/python" -c 'import tkinter' >/dev/null 2>&1; then
        warn "Existing environment is broken (its Python was upgraded or removed); recreating it."
        rm -rf "$VENV"
    fi
    [ -x "$VENV/bin/python" ] || "$PY" -m venv "$VENV"
    info "Installing the app into $VENV"
    "$VENV/bin/python" -m pip install --quiet --disable-pip-version-check --upgrade pip
    # Build from a temporary copy so pip doesn't leave build/ and *.egg-info in the source tree.
    local build_dir
    build_dir="$(mktemp -d)"
    (cd "$SRC" && tar -cf - pyproject.toml readme.md LICENSE password_manager) | tar -xf - -C "$build_dir"
    "$VENV/bin/python" -m pip install --quiet --disable-pip-version-check --upgrade "$build_dir"
    rm -rf "$build_dir"
    VERSION="$("$VENV/bin/python" -c 'import password_manager as p; print(p.__version__)')"
}

configure() {
    local args=(-m password_manager setup)
    [ "$RECONFIGURE" -eq 1 ] && args+=(--reconfigure)
    # Ubuntu/Debian MySQL and MariaDB let the OS root user in via unix_socket, so `sudo mysql` works.
    if [ "$OS" = Linux ] && [ "${#SUDO[@]}" -gt 0 ]; then args+=(--admin-command "sudo mysql"); fi
    if [ "$OS" = Linux ] && [ "${#SUDO[@]}" -eq 0 ]; then args+=(--admin-command "mysql"); fi
    if [ -n "${PM_SETUP_ARGS:-}" ]; then
        local extra
        read -r -a extra <<<"$PM_SETUP_ARGS"
        args+=("${extra[@]}")
    fi
    if have_tty; then
        "$VENV/bin/python" "${args[@]}" </dev/tty
    else
        "$VENV/bin/python" "${args[@]}"
    fi
}

main() {
    RECONFIGURE=0 UNINSTALL=0 LAUNCH=1
    local arg
    for arg in "$@"; do
        case "$arg" in
            --reconfigure) RECONFIGURE=1 ;;
            --uninstall) UNINSTALL=1 ;;
            --no-launch) LAUNCH=0 ;;
            -h|--help) usage; exit 0 ;;
            *) die "Unknown option: $arg (see --help)" ;;
        esac
    done

    OS="$(uname -s)"
    case "$OS" in
        Darwin) INSTALL_DIR="$HOME/Library/Application Support/PasswordManager/app" ;;
        Linux)  INSTALL_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/password-manager/app" ;;
        *) die "Unsupported system: $OS. On Windows, double-click install.bat." ;;
    esac
    VENV="$INSTALL_DIR/venv"
    LAUNCH_CMD=()
    VERSION="?"

    if [ "$UNINSTALL" -eq 1 ]; then
        rm -rf "$INSTALL_DIR"
        if [ "$OS" = Darwin ]; then mac_uninstall_launcher; else linux_uninstall_launcher; fi
        info "Removed the app. Your vault and settings were kept:"
        echo "    - MySQL database 'password_manager' and MySQL user 'pm_app'"
        if [ "$OS" = Darwin ]; then
            echo "    - config + GPG credential in: $HOME/Library/Application Support/PasswordManager"
        else
            echo "    - config + GPG credential in: ${XDG_CONFIG_HOME:-$HOME/.config}/password-manager"
        fi
        echo "  To erase everything, drop that database and user in MySQL and delete that folder."
        exit 0
    fi

    if [ "$(id -u)" -eq 0 ] && [ "$OS" = Darwin ]; then
        die "Run this as your normal user, not with sudo."
    fi

    resolve_source
    if [ "$OS" = Darwin ]; then mac_deps; else linux_deps; fi
    install_app
    configure
    if [ "$OS" = Darwin ]; then mac_launcher; else linux_launcher; fi

    info "Password Manager $VERSION is installed."
    if [ "$LAUNCH" -eq 1 ] && [ "${#LAUNCH_CMD[@]}" -gt 0 ]; then
        info "Opening it now..."
        "${LAUNCH_CMD[@]}" >/dev/null 2>&1 &
        disown 2>/dev/null || true
    fi
}

# Everything runs inside main, so a `curl | bash` pipe is fully read before anything executes.
main "$@"
