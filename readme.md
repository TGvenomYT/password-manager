<h1 align="center">
✨🔐 <span style="background: linear-gradient(90deg,#00C9FF,#92FE9D); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">Password Manager MARK IV</span> 🔐✨
</h1>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9%2B-blue?logo=python&logoColor=white" alt="Python Badge"/>
  <img src="https://img.shields.io/badge/MySQL-Database-blue?logo=mysql&logoColor=white" alt="MySQL Badge"/>
  <img src="https://img.shields.io/badge/Fernet-Encryption-green" alt="Fernet Badge"/>
  <img src="https://img.shields.io/badge/GnuPG-Credentials-0093DD?logo=gnuprivacyguard&logoColor=white" alt="GnuPG Badge"/>
  <img src="https://img.shields.io/badge/License-MIT-yellow" alt="License Badge"/>
</p>

<p align="center">
  🧠 <b>Secured. Simple. Smart.</b>
  <br>
  A lightweight password manager using <b>Fernet Encryption</b> & <b>MySQL</b> for secure local storage,
  <br>
  with a Tkinter GUI 🪟 that runs on <b>macOS, Linux and Windows</b>.
</p>

---

## 🚀 Features

✅ Add, View, and Delete Passwords
✅ Every password encrypted with **Fernet** (AES-128-CBC + HMAC-SHA256)
✅ Encryption key protected by your **master password** (scrypt), never stored in plaintext
✅ MySQL login protected by **GnuPG** (AES-256), with a dedicated least-privilege MySQL user
✅ Brute-force protection: growing lockout after 5 wrong master passwords, and **no data is ever deleted**
✅ **One-click installers** for macOS, Linux and Windows
✅ 100% local: no cloud, no telemetry

---

## 📦 Install

| OS | One click | Or from a terminal |
|---|---|---|
| 🍎 **macOS** 11+ | Double-click **`install.command`** | `./install.sh` |
| 🐧 **Linux** (Ubuntu, Debian, Fedora, Arch) | – | `./install.sh` |
| 🪟 **Windows** 10/11 | Double-click **`install.bat`** | `powershell -ExecutionPolicy Bypass -File install.ps1` |

Without cloning the repo (macOS/Linux):

```bash
curl -fsSL https://raw.githubusercontent.com/TGvenomYT/password-manager/main/install.sh | bash
```

The installer:

1. Installs **Python 3 + Tkinter**, **GnuPG** and **MySQL** if they're missing (Homebrew on macOS; apt, dnf or pacman on Linux; winget on Windows) and starts MySQL.
2. Installs the app into its own virtual environment and **builds a native app for your machine** with PyInstaller: `Password Manager.app` on macOS, `PasswordManager.exe` on Windows, a `PasswordManager` binary on Linux. If that build fails, the app runs from the Python environment instead (set `PM_NO_BINARY=1` to skip the build).
3. Creates the `password_manager` database and a MySQL user `pm_app` with a random password, which can only access that database. The app never logs in as `root`.
4. Asks you for a **GPG passphrase** and uses it to encrypt that MySQL password on disk.
5. Adds a launcher: `~/Applications/Password Manager.app` on macOS, an applications-menu entry on Linux, Start Menu and Desktop shortcuts on Windows.

On first launch the app asks you to create your **master password**.

> **macOS note:** if Finder says `install.command` "can't be opened", right-click it and choose **Open**, or run `./install.sh` in Terminal.

Other installer options: `--reconfigure` (redo the database/GPG setup), `--uninstall` (remove the app but keep your vault), `--no-launch`. On Windows: `-Reconfigure`, `-Uninstall`, `-NoLaunch`.

---

## 🔑 How It Works

You use two secrets:

| Secret | Protects | When you type it |
|---|---|---|
| **GPG passphrase** | The MySQL password, stored as `db-credential.gpg` | At launch, unless gpg-agent still remembers it (about 10 minutes) |
| **Master password** | Your vault: the key that decrypts your passwords | Every time you open the vault |

```
master password ──scrypt (128 MiB, random salt)──▶ key-encryption key
                                                       │ unwraps
                                                       ▼
vault_meta.wrapped_key ──────────────────────────▶ data key (Fernet)
                                                       │ decrypts
                                                       ▼
passwords.password ──────────────────────────────▶ your passwords
```

- The **data key** is random and only stored *wrapped* (encrypted) with a key derived from your master password. Someone who copies the whole database can't decrypt anything without the master password, and each guess costs them a 128 MiB scrypt computation.
- After **5 wrong master passwords** the vault locks for 30 seconds, then 60, 120, and so on up to 1 hour. The counter is stored in the database, so restarting the app doesn't reset it.
- Files are stored per user, with owner-only permissions:
  - macOS: `~/Library/Application Support/PasswordManager/`
  - Linux: `~/.config/password-manager/`
  - Windows: `%APPDATA%\PasswordManager\`

⚠️ **There is no recovery.** If you forget the master password, the vault can't be decrypted. Nobody, including the developer, can get it back.

---

## ⬆️ Upgrading from v2.x

Run the installer. On your first unlock, the app automatically upgrades an old database:

- Your **existing master password keeps working**.
- The old plaintext key in the `locker` table is replaced. A new data key is generated, every saved password is re-encrypted with it, the new key is wrapped with your master password, and the `locker` table is deleted. This all happens in one transaction, so it either completes fully or changes nothing.
- The old `passwd.txt.gpg` and `root` login are no longer used. Setup asks for the MySQL `root` password **once**, to create the `pm_app` user.

<details>
<summary><b>What was wrong with the old key handling (fixed in 3.0)</b></summary>

- The Fernet key was stored **in plaintext** in the `locker` table, next to the encrypted passwords. Anyone with database access could decrypt everything; the master password was only a check in the GUI.
- The key and the master password hash were written as **two separate half-empty rows**. The "does a key exist?" check (`SELECT … LIMIT 1`) matched either row, and other versions of the code assumed a single row.
- `password VARCHAR(255)` was too short for the encrypted form of passwords longer than about 127 characters, so saving them failed.
- 5 wrong master passwords ran `DROP DATABASE`, deleting the whole vault, but the counter reset on restart, so it only ever hurt the real user.
- `auth_plugin='mysql_native_password'` fails on MySQL 9, which removed that plugin.
- With bcrypt 5, master passwords over 72 bytes crashed the app.
</details>

---

## 🛠️ Manual setup (advanced)

Requirements: Python 3.9+ with Tkinter, GnuPG 2.2+, and MySQL 8+ or MariaDB 10.5+.

```bash
python3 -m venv venv && . venv/bin/activate
pip install .
python -m password_manager setup              # add --admin-command "sudo mysql" on Ubuntu/Debian
python -m password_manager                    # launch

# optional: build a standalone app for this machine
pip install "pyinstaller>=6.11" && pyinstaller --noconfirm packaging/PasswordManager.spec
dist/PasswordManager --self-test              # macOS: "dist/Password Manager.app/Contents/MacOS/PasswordManager"
```

`setup` options: `--host`, `--port`, `--socket`, `--database`, `--app-user`, `--admin-user`, `--admin-command`, `--reconfigure`.

## 🧯 Troubleshooting

| Problem | Fix |
|---|---|
| "Could not connect to MySQL" | Start the server: `brew services start mysql` / `sudo systemctl start mysql` / the *PasswordManagerMySQL* service |
| Forgot the GPG passphrase | `./install.sh --reconfigure` (your vault is unaffected) |
| gpg seems stuck | `gpgconf --kill gpg-agent` |
| Something else | Check `password-manager.log` in the settings folder above |

## 🧪 Development

```bash
pip install -e ".[test]"
pytest                                                   # unit tests
PM_TEST_MYSQL="root:password@127.0.0.1:3306" pytest     # plus database tests (uses throwaway databases)
```

---

## 🎬 Screenshots / Demo

<p align="center">
  <img src="screenshots/Screenshot from 2025-10-08 21-30-17.png" width="70%" alt="GUI Screenshot"/>
</p>

---

## 🌈 About the Project

> **MARK IV** is designed for users who value **simplicity and privacy**.
> Built with 💙 and Python, it keeps your credentials safe, right on your device.

---

## 💬 Connect With Me

<p align="center">
  <a href="https://github.com/TGvenomYT">
    <img src="https://img.shields.io/badge/GitHub-000?style=for-the-badge&logo=github&logoColor=white"/>
  </a>
  <a href="https://Discord.com/users/tgvenom0441">
     <img src="https://img.shields.io/badge/Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white"/>
  </a>
  <a href="mailto:rajicbe1969@gmail.com">
    <img src="https://img.shields.io/badge/Email-D14836?style=for-the-badge&logo=gmail&logoColor=white"/>
  </a>
</p>
