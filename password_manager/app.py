"""Tkinter GUI. The screens keep the original layouts and artwork."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from tkinter import (
    Button, Canvas, Entry, Frame, Label, PhotoImage, Scrollbar, Text, Tk, Toplevel, messagebox,
)
from typing import Callable, List, Optional, Sequence, Tuple

import mysql.connector

from . import config as cfgmod
from . import credentials, db
from .vault import (
    MIN_MASTER_PASSWORD_LENGTH, Vault, VaultError, VaultLocked, WrongMasterPassword,
    check_master_password_strength, format_duration, FREE_ATTEMPTS,
)

log = logging.getLogger(__name__)
ASSETS = Path(__file__).resolve().parent / "assets"
TITLE = "Password Manager"

# (file, x, y) canvas images, in drawing order, taken from the original designs.
MENU_IMAGES = [("image_1.png", 941, 473), ("image_2.png", 874, 475), ("image_3.png", 798, 471),
               ("image_4.png", 849, 129), ("image_5.png", 225, 250), ("image_6.png", 572, 373)]
ADD_BACKGROUND = [("image_1.png", 414, 253)]
ADD_IMAGES = [("image_2.png", 24, 480), ("image_3.png", 414, 455), ("image_4.png", 178, 243),
              ("image_5.png", 733, 472), ("image_6.png", 664, 65), ("image_7.png", 797, 474),
              ("image_8.png", 178, 375), ("image_9.png", 664, 318), ("image_10.png", 534, 474),
              ("image_11.png", 467, 203), ("image_12.png", 607, 474), ("image_13.png", 671, 472),
              ("image_14.png", 40, 172)]
VIEW_IMAGES = [("image_1.png", 609, 303), ("image_2.png", 95, 303), ("image_3.png", 100, 513),
               ("image_4.png", 130, 218), ("image_5.png", 1000, 37), ("image_6.png", 781, 50),
               ("entry_1.png", 609.5, 314)]
DELETE_IMAGES = [("image_1.png", 351, 208), ("image_2.png", 351, 143), ("image_3.png", 351, 43),
                 ("image_4.png", 30, 40), ("image_5.png", 671, 40)]
DELETE_PLACEHOLDER = "enter username to delete the password"


# --------------------------------------------------------------------------- helpers

def _canvas(win, width: int, height: int, bg: str) -> Canvas:
    win.geometry(f"{width}x{height}")
    win.configure(bg=bg)
    win.resizable(False, False)
    canvas = Canvas(win, bg=bg, height=height, width=width, bd=0, highlightthickness=0, relief="ridge")
    canvas.place(x=0, y=0)
    if not hasattr(win, "_images"):
        win._images = []  # keep PhotoImage references alive (Tk drops unreferenced images)
    return canvas


def _image(win, folder: str, name: str) -> PhotoImage:
    img = PhotoImage(master=win, file=str(ASSETS / folder / name))
    win._images.append(img)
    return img


def _draw(win, canvas: Canvas, folder: str, images: Sequence[Tuple[str, float, float]]) -> None:
    for name, x, y in images:
        canvas.create_image(x, y, image=_image(win, folder, name))


def _image_button(win, folder: str, name: str, text: str, command, box) -> Button:
    button = Button(win, text=text, image=_image(win, folder, name), compound="center",
                    borderwidth=0, highlightthickness=0, relief="flat", command=command)
    x, y, w, h = box
    button.place(x=x, y=y, width=w, height=h)
    return button


def _plain_button(parent, text: str, command) -> Button:
    # macOS draws native buttons and ignores bg, so white-on-black text would be invisible there.
    style = {} if sys.platform == "darwin" else dict(
        bg="black", fg="white", activebackground="#333333", activeforeground="white")
    return Button(parent, text=text, command=command, **style)


def _busy(widget, busy: bool) -> None:
    widget.configure(cursor="watch" if busy else "")
    widget.update_idletasks()


def _raise_window(win) -> None:
    win.lift()
    win.attributes("-topmost", True)
    win.after(300, lambda: win.attributes("-topmost", False))
    win.focus_force()


def ask_secret(root: Tk, title: str, prompt: str) -> Optional[str]:
    """Modal password prompt in the master-password style. Returns None if cancelled."""
    dialog = Toplevel(root)
    dialog.title(title)
    dialog.geometry("570x200")
    dialog.resizable(False, False)
    dialog.configure(bg="black")
    Label(dialog, text=prompt, bg="black", fg="white", wraplength=500, justify="center").place(
        x=35, y=18, width=500, height=40)
    entry = Entry(dialog, borderwidth=3, show="*")
    entry.place(x=121, y=68, width=320, height=40)
    result: List[Optional[str]] = [None]

    def submit(_event=None):
        result[0] = entry.get()
        dialog.destroy()

    _plain_button(dialog, "Unlock", submit).place(x=140, y=128, width=130, height=31)
    _plain_button(dialog, "Cancel", dialog.destroy).place(x=300, y=128, width=130, height=31)
    entry.bind("<Return>", submit)
    dialog.bind("<Escape>", lambda _e: dialog.destroy())
    _raise_window(dialog)
    entry.focus_set()
    dialog.grab_set()
    root.wait_window(dialog)
    return result[0]


# --------------------------------------------------------------------------- app

class App:
    def __init__(self, root: Tk, vault: Vault, on_close: Callable[[], None]) -> None:
        self.root = root
        self.vault = vault
        self._on_close = on_close
        root.title(TITLE)
        root.protocol("WM_DELETE_WINDOW", self.quit)

    def quit(self) -> None:
        self.vault.lock()
        try:
            self._on_close()
        finally:
            self.root.destroy()

    def _clear(self) -> None:
        for child in self.root.winfo_children():
            child.destroy()
        self.root._images = []

    # ------------------------------------------------------------ master password

    def show_create_master(self) -> None:
        self._clear()
        root = self.root
        root.title(f"{TITLE}: create master password")
        root.geometry("570x270")
        root.resizable(False, False)
        root.configure(bg="black")
        Label(root, text="Create your master password. It encrypts your vault, and it can't be\n"
                         "recovered if you forget it.", bg="black", fg="white").place(x=35, y=10, width=500, height=40)
        Label(root, text="Master password", bg="black", fg="white", anchor="w").place(x=121, y=52, width=320)
        first = Entry(root, borderwidth=3, show="*")
        first.place(x=121, y=74, width=320, height=36)
        Label(root, text="Confirm master password", bg="black", fg="white", anchor="w").place(x=121, y=114, width=320)
        second = Entry(root, borderwidth=3, show="*")
        second.place(x=121, y=136, width=320, height=36)
        status = Label(root, text=f"At least {MIN_MASTER_PASSWORD_LENGTH} characters.", bg="black", fg="#bbbbbb")
        status.place(x=35, y=228, width=500)

        def store(_event=None):
            password = first.get()
            if password != second.get():
                status.config(text="The passwords don't match.", fg="#ff6b6b")
                return
            try:
                check_master_password_strength(password)
                _busy(root, True)
                self.vault.create(password)
            except VaultError as exc:
                status.config(text=str(exc), fg="#ff6b6b")
                return
            finally:
                _busy(root, False)
            messagebox.showinfo("Success", "Master password set. Your vault is ready.", parent=root)
            self.show_menu()

        _plain_button(root, "Submit", store).place(x=217, y=186, width=147, height=31)
        second.bind("<Return>", store)
        first.bind("<Return>", lambda _e: second.focus_set())
        _raise_window(root)
        first.focus_set()

    def show_unlock(self) -> None:
        self._clear()
        root = self.root
        root.title(f"{TITLE}: master password")
        root.geometry("570x270")
        root.resizable(False, False)
        root.configure(bg="black")
        Label(root, text="Enter the master password to open the software", bg="black", fg="white").place(
            x=35, y=30, width=500)
        entry = Entry(root, borderwidth=3, show="*")
        entry.place(x=121, y=72, width=320, height=43)
        status = Label(root, text="", bg="black", fg="#ff6b6b", wraplength=520)
        status.place(x=25, y=180, width=520, height=60)
        button = _plain_button(root, "Submit", None)
        button.place(x=217, y=132, width=147, height=31)

        def countdown():
            if not entry.winfo_exists():
                return
            remaining = self.vault.lockout_remaining()
            if remaining > 0:
                button.config(state="disabled")
                entry.config(state="disabled")
                status.config(text=f"Too many failed attempts. Try again in {format_duration(remaining)}.")
                root.after(1000, countdown)
            else:
                button.config(state="normal")
                entry.config(state="normal")
                status.config(text="")
                entry.focus_set()

        def check(_event=None):
            if str(button["state"]) == "disabled":
                return
            try:
                _busy(root, True)
                self.vault.unlock(entry.get())
            except WrongMasterPassword as exc:
                entry.delete(0, "end")
                if exc.locked_for:
                    countdown()
                else:
                    left = FREE_ATTEMPTS - exc.failed_attempts
                    status.config(text=f"Wrong master password. {left} attempt{'s' if left != 1 else ''} "
                                       "left before a temporary lockout.")
                return
            except VaultLocked:
                countdown()
                return
            except VaultError as exc:
                messagebox.showerror("Error", str(exc), parent=root)
                return
            finally:
                _busy(root, False)
            self.show_menu()

        button.config(command=check)
        entry.bind("<Return>", check)
        _raise_window(root)
        countdown()

    # --------------------------------------------------------------------- menu

    def show_menu(self) -> None:
        self._clear()
        root = self.root
        root.title("Menu")
        canvas = _canvas(root, 981, 500, "#A9CEE9")
        _draw(root, canvas, "menu", MENU_IMAGES)
        _image_button(root, "menu", "button_1.png", "Add password", self.open_add, (515, 70, 190, 48))
        _image_button(root, "menu", "button_2.png", "View Password", self.open_view, (515, 163, 190, 48))
        _image_button(root, "menu", "button_3.png", "Delete Password", self.open_delete, (753, 322, 127, 37))

    # ---------------------------------------------------------------------- add

    def open_add(self) -> Toplevel:
        win = Toplevel(self.root)
        win.title("Add Password")
        canvas = _canvas(win, 829, 506, "#69F8B1")
        _draw(win, canvas, "add", ADD_BACKGROUND)
        canvas.create_rectangle(100, 84, 442, 131, fill="#FFFFFF", outline="")
        canvas.create_rectangle(100, 206, 442, 253, fill="#FFFFFF", outline="")
        canvas.create_text(96, 54, anchor="nw", text="Enter Username:", fill="#000000", font=("Inter", -20))
        canvas.create_text(100, 176, anchor="nw", text="Enter Password:", fill="#000000", font=("Inter", -20))
        username = Entry(win, borderwidth=3)
        username.place(x=100, y=84, width=342, height=47)
        password = Entry(win, borderwidth=3, show="*")
        password.place(x=100, y=205, width=342, height=47)

        def add(_event=None):
            try:
                self.vault.add_entry(username.get(), password.get())
            except ValueError as exc:
                messagebox.showerror("Error", str(exc), parent=win)
                return
            except (VaultError, mysql.connector.Error) as exc:
                log.exception("add failed")
                messagebox.showerror("Error", f"Could not save the password: {exc}", parent=win)
                return
            messagebox.showinfo("Success", "Password Added Successfully", parent=win)
            username.delete(0, "end")
            password.delete(0, "end")
            username.focus_set()

        _image_button(win, "add", "button_1.png", "Quit", win.destroy, (314, 359, 181, 41))
        _image_button(win, "add", "button_2.png", "Submit", add, (560, 136, 179, 40))
        _draw(win, canvas, "add", ADD_IMAGES)
        password.bind("<Return>", add)
        username.focus_set()
        return win

    # --------------------------------------------------------------------- view

    def open_view(self) -> Optional[Toplevel]:
        try:
            entries = self.vault.entries()
        except (VaultError, mysql.connector.Error) as exc:
            log.exception("view failed")
            messagebox.showerror("Error", f"Could not load passwords: {exc}", parent=self.root)
            return None
        win = Toplevel(self.root)
        win.title("View Passwords")
        canvas = _canvas(win, 1020, 606, "#EBD971")
        _draw(win, canvas, "view", VIEW_IMAGES[:5])
        _image_button(win, "view", "button_1.png", "Quit", win.destroy, (800, 520, 164, 36))
        _draw(win, canvas, "view", VIEW_IMAGES[5:])
        canvas.create_text(424, 49, anchor="nw", text="Viewing Passwords", fill="#000000", font=("Inter", -32))

        frame = Frame(win, bg="#EBD971")
        frame.place(x=294, y=119, width=632, height=390)
        text = Text(frame, font=("Bold", 16), bg="black", fg="white", bd=5, wrap="none")
        text.pack(side="left", fill="both", expand=True)
        scrollbar = Scrollbar(frame, orient="vertical", command=text.yview)
        scrollbar.pack(side="right", fill="y")
        text.config(yscrollcommand=scrollbar.set)
        if not entries:
            text.insert("end", "No passwords saved yet.\n")
        for entry in entries:
            shown = entry.password if entry.password is not None else "[cannot be decrypted]"
            text.insert("end", f"{entry.username} | {shown}\n")
        text.config(state="disabled")
        return win

    # ------------------------------------------------------------------- delete

    def open_delete(self) -> Toplevel:
        win = Toplevel(self.root)
        win.title("Delete Password")
        canvas = _canvas(win, 702, 417, "#FFFFFF")
        _draw(win, canvas, "delete", DELETE_IMAGES[:2])
        entry = Entry(win, borderwidth=3)
        entry.place(x=124, y=122, width=452, height=45)
        normal_fg = entry.cget("fg")  # system colour, correct in light and dark mode
        entry.config(fg="grey")
        entry.insert(0, DELETE_PLACEHOLDER)
        placeholder = [True]

        def clear_placeholder(_event=None):
            if placeholder[0]:
                placeholder[0] = False
                entry.delete(0, "end")
                entry.config(fg=normal_fg)

        def delete(_event=None):
            name = "" if placeholder[0] else entry.get().strip()
            if not name:
                messagebox.showerror("Error", "Enter the username to delete.", parent=win)
                return
            if not messagebox.askyesno("Confirm", f"Delete every saved password for '{name}'?", parent=win):
                return
            try:
                count = self.vault.delete_by_username(name)
            except (VaultError, mysql.connector.Error) as exc:
                log.exception("delete failed")
                messagebox.showerror("Error", f"Could not delete: {exc}", parent=win)
                return
            if count:
                messagebox.showinfo("Success", "Password Deleted Successfully", parent=win)
                win.destroy()
            else:
                messagebox.showinfo("Not found", f"No saved password for '{name}'.", parent=win)

        entry.bind("<FocusIn>", clear_placeholder)
        entry.bind("<Key>", clear_placeholder)
        entry.bind("<Return>", delete)
        _image_button(win, "delete", "button_1.png", "cancel", win.destroy, (271, 287, 166, 38))
        _image_button(win, "delete", "button_2.png", "Delete", delete, (271, 224, 166, 38))
        _draw(win, canvas, "delete", DELETE_IMAGES[2:3])
        canvas.create_text(67, 24, anchor="nw", text="You are about to delete the password",
                           fill="#000000", font=("Inter", -32))
        _draw(win, canvas, "delete", DELETE_IMAGES[3:])
        return win


# --------------------------------------------------------------------------- startup

def _fatal(root: Tk, message: str) -> int:
    log.error(message)
    messagebox.showerror(TITLE, message, parent=root)
    root.destroy()
    return 1


def run() -> int:
    root = Tk()
    root.withdraw()
    root.title(TITLE)
    try:
        cfg = cfgmod.load()
    except cfgmod.ConfigError as exc:
        return _fatal(root, f"{exc}\n\nRun the installer again, or run:\n    python -m password_manager setup")

    try:
        gpg = credentials.find_gpg(cfg.gpg_binary)

        def ask(attempt: int) -> Optional[str]:
            prompt = "Enter your GPG passphrase to unlock the database connection."
            if attempt:
                prompt = "Wrong GPG passphrase. Try again."
            return ask_secret(root, TITLE, prompt)

        db_password = credentials.unlock_db_password(cfg.credential_path(), gpg, ask)
    except credentials.PassphraseCancelled:
        root.destroy()
        return 1
    except credentials.GpgError as exc:
        return _fatal(root, f"Could not decrypt the database credential:\n{exc}")

    try:
        conn = db.connect(cfg.db, db_password)
    except mysql.connector.Error as exc:
        return _fatal(
            root,
            f"Could not connect to MySQL as '{cfg.db.user}':\n{exc}\n\n"
            "Make sure the MySQL server is running (macOS: brew services start mysql, "
            "Linux: sudo systemctl start mysql, Windows: Services, then MySQL)."
        )
    del db_password

    vault = Vault(conn)
    try:
        vault.ensure_schema()
        needs_setup = vault.needs_master_password_setup()
    except (VaultError, mysql.connector.Error) as exc:
        conn.close()
        return _fatal(root, f"Could not open the vault:\n{exc}")

    app = App(root, vault, on_close=conn.close)
    root.deiconify()
    if needs_setup:
        app.show_create_master()
    else:
        app.show_unlock()
    root.mainloop()
    return 0


def main() -> int:
    try:
        return run()
    except Exception:  # last resort: log it, and tell the user instead of dying silently
        log.exception("Unhandled error")
        try:
            messagebox.showerror(TITLE, "Unexpected error. Details were written to the log:\n"
                                 + str(cfgmod.config_dir() / "password-manager.log"))
        except Exception:
            pass
        return 1


if __name__ == "__main__":
    sys.exit(main())
