"""Tkinter GUI. The screens keep the original layouts and artwork."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from datetime import date
from tkinter import (
    Canvas, Entry, Frame, PhotoImage, Scrollbar, TclError, Text, Tk, Toplevel, filedialog, messagebox,
)
from typing import Callable, List, Optional, Sequence, Tuple

import mysql.connector

from . import config as cfgmod
from . import credentials, crypto, db
from .vault import (
    MIN_MASTER_PASSWORD_LENGTH, Vault, VaultError, VaultLocked, WrongMasterPassword, WrongRecoveryKey,
    check_master_password_strength, format_duration, FREE_ATTEMPTS,
)

log = logging.getLogger(__name__)
ASSETS = Path(__file__).resolve().parent / "assets"
APP_ICON = ASSETS / "app-icon.png"
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

# Master-password screens: a pink-to-purple gradient with the artwork on the pink side.
# Pills and artwork come from assets/master.
MASTER_PINK = (0xF9, 0xC9, 0xDD)
MASTER_PURPLE = (0xBB, 0xA7, 0xF6)
MASTER_BG = "#BBA7F6"
MASTER_INK = "#141414"
MASTER_MUTED = "#3B365C"
MASTER_ERROR = "#861A14"
MASTER_LINK = "#2B2A7A"
MONO = {"darwin": "Menlo", "win32": "Consolas"}.get(sys.platform, "DejaVu Sans Mono")
# The add/delete designs have white input boxes; without explicit colours macOS dark mode paints them black.
WHITE_FIELD = dict(bg="#FFFFFF", fg="#141414", insertbackground="#141414")


# --------------------------------------------------------------------------- helpers

def _set_app_icon(root: Tk) -> None:
    """Give every window the app icon. On macOS this also sets the Dock icon when the app runs
    from source; the built .app already gets it from icon.icns, so leave that alone."""
    if sys.platform == "darwin" and getattr(sys, "frozen", False):
        return
    try:
        root._app_icon = PhotoImage(master=root, file=str(APP_ICON))  # keep a reference
        root.iconphoto(True, root._app_icon)
    except TclError:  # e.g. Tk 8.5, which can't read PNG
        log.debug("could not set the window icon", exc_info=True)


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


def _image_button(win, canvas: Canvas, folder: str, name: str, text: str, command, box) -> "_Pill":
    """One of the original pill buttons, drawn on the canvas at box = (x, y, width, height)."""
    x, y, w, h = box
    pill = _Pill(win, canvas, x + w / 2, y + h / 2, text, command, name, folder=folder, size=-14)
    # Artwork drawn after the button must not cover it (a Button widget always sat on top).
    win.after_idle(lambda: canvas.winfo_exists() and canvas.tag_raise(pill.tag))
    return pill


class _Pill:
    """A rounded button drawn on the canvas. Unlike an image Button, macOS draws no grey
    corners around it."""

    def __init__(self, win, canvas: Canvas, x: float, y: float, text: str, command,
                 image: str, disabled_image: Optional[str] = None, size: int = -16, folder: str = "master") -> None:
        self.canvas = canvas
        self.command = command
        self.enabled = True
        self._on = _image(win, folder, image)
        self._off = _image(win, folder, disabled_image) if disabled_image else self._on
        self.tag = tag = f"pill{id(self)}"
        self._item = canvas.create_image(x, y, image=self._on, tags=tag)
        canvas.create_text(x, y, text=text, fill=MASTER_INK, font=("Inter", size), tags=tag)
        canvas.tag_bind(tag, "<Button-1>", self.invoke)
        canvas.tag_bind(tag, "<Enter>", lambda _e: canvas.config(cursor="hand2" if self.enabled else ""))
        canvas.tag_bind(tag, "<Leave>", lambda _e: canvas.config(cursor=""))

    def invoke(self, _event=None) -> None:
        if self.enabled:
            self.command()

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled
        self.canvas.itemconfig(self._item, image=self._on if enabled else self._off)


def _master_canvas(win, width: int, height: int, panel: int, art: Tuple[str, str]) -> Canvas:
    """Pink-to-purple page with one illustration centred in the first `panel` pixels."""
    canvas = _canvas(win, width, height, MASTER_BG)
    step = 2  # Tk canvases have no gradient fill, so paint it in thin strips
    for x in range(0, width, step):
        t = x / max(1, width - step)
        r, g, b = (round(a + (c - a) * t) for a, c in zip(MASTER_PINK, MASTER_PURPLE))
        canvas.create_rectangle(x, 0, x + step, height, fill=f"#{r:02x}{g:02x}{b:02x}", outline="")
    canvas.create_image(panel / 2, height / 2, image=_image(win, *art))
    return canvas


def _master_link(canvas: Canvas, x: int, y: int, text: str, command) -> int:
    item = canvas.create_text(x, y, anchor="w", text=text, fill=MASTER_LINK, font=("Inter", -14, "underline"))
    canvas.tag_bind(item, "<Button-1>", lambda _e: command())
    canvas.tag_bind(item, "<Enter>", lambda _e: canvas.config(cursor="hand2"))
    canvas.tag_bind(item, "<Leave>", lambda _e: canvas.config(cursor=""))
    return item


def _master_title(win, canvas: Canvas, x: int, y: int, text: str, size: int = -34) -> None:
    item = canvas.create_text(x, y, anchor="nw", text=text, fill=MASTER_INK, font=("Inter", size))
    _x1, y1, x2, y2 = canvas.bbox(item)
    canvas.create_image(x2 + 34, (y1 + y2) / 2, image=_image(win, "master", "padlock.png"))


def _master_text(canvas: Canvas, x: int, y: int, text: str, width: int, size: int = -16,
                 fill: str = MASTER_MUTED) -> int:
    return canvas.create_text(x, y, anchor="nw", text=text, fill=fill, width=width, font=("Inter", size))


def _secret_field(win, canvas: Canvas, x: int, y: int, small: bool = False, masked: bool = True) -> Entry:
    """A white rounded input; (x, y) is its top-left corner. Masked unless it's for a recovery key."""
    width, height = (380, 50) if small else (420, 54)
    canvas.create_image(x, y, anchor="nw", image=_image(win, "master", "field_small.png" if small else "field.png"))
    entry = Entry(win, show="\u2022" if masked else "", bd=0, relief="flat", highlightthickness=0,
                  font=("Inter", -18) if masked else (MONO, -18),
                  bg="#FFFFFF", fg=MASTER_INK, insertbackground=MASTER_INK,
                  disabledbackground="#FFFFFF", disabledforeground="#9A97B0")
    entry.place(x=x + 16, y=y + 9, width=width - 32, height=height - 18)
    return entry


def _busy(widget, busy: bool) -> None:
    widget.configure(cursor="watch" if busy else "")
    widget.update_idletasks()


def _raise_window(win) -> None:
    win.lift()
    win.attributes("-topmost", True)
    win.after(300, lambda: win.attributes("-topmost", False))
    win.focus_force()


def ask_secret(root: Tk, title: str, prompt: str) -> Optional[str]:
    """Modal passphrase prompt in the master-password style. Returns None if cancelled."""
    dialog = Toplevel(root)
    dialog.title(title)
    canvas = _master_canvas(dialog, 640, 320, 200, ("master", "safe.png"))
    _master_title(dialog, canvas, 236, 34, "Unlock the database", size=-26)
    _master_text(canvas, 238, 84, prompt, width=370)
    entry = _secret_field(dialog, canvas, 236, 142, small=True)
    result: List[Optional[str]] = [None]

    def submit(_event=None):
        result[0] = entry.get()
        dialog.destroy()

    _Pill(dialog, canvas, 321, 248, "Unlock", submit, "pill_green_small.png")
    _Pill(dialog, canvas, 503, 248, "Cancel", dialog.destroy, "pill_red_small.png")
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
        canvas = _master_canvas(root, 820, 520, 300, ("menu", "image_4.png"))
        _master_title(root, canvas, 350, 44, "Create your vault")
        _master_text(canvas, 352, 100, "Your master password encrypts everything you save. "
                     "Next you'll get a recovery key, in case you ever forget it.", width=430)
        _master_text(canvas, 352, 168, "Master password", width=420, size=-15, fill=MASTER_INK)
        first = _secret_field(root, canvas, 350, 192)
        _master_text(canvas, 352, 262, "Confirm master password", width=420, size=-15, fill=MASTER_INK)
        second = _secret_field(root, canvas, 350, 286)
        status = _master_text(canvas, 352, 354, f"At least {MIN_MASTER_PASSWORD_LENGTH} characters.",
                              width=430, size=-15)

        def fail(message: str) -> None:
            canvas.itemconfig(status, text=message, fill=MASTER_ERROR)

        def store(_event=None):
            password = first.get()
            if password != second.get():
                fail("The passwords don't match.")
                return
            try:
                check_master_password_strength(password)
                _busy(root, True)
                self.vault.create(password)
            except VaultError as exc:
                fail(str(exc))
                return
            finally:
                _busy(root, False)
            self.show_recovery_key("created")

        _Pill(root, canvas, 445, 440, "Create vault", store, "pill_green.png")
        second.bind("<Return>", store)
        first.bind("<Return>", lambda _e: second.focus_set())
        _raise_window(root)
        first.focus_set()

    def show_unlock(self) -> None:
        self._clear()
        root = self.root
        root.title(f"{TITLE}: master password")
        canvas = _master_canvas(root, 820, 460, 300, ("master", "shield_key.png"))
        _master_title(root, canvas, 350, 70, "Welcome back")
        _master_text(canvas, 352, 126, "Enter your master password to open your vault.", width=430)
        entry = _secret_field(root, canvas, 350, 176)
        button = _Pill(root, canvas, 445, 290, "Unlock", None, "pill_green.png", "pill_off.png")
        _master_link(canvas, 566, 290, "Forgot your master password?", self.show_recover)
        status = _master_text(canvas, 352, 336, "", width=430, size=-15, fill=MASTER_ERROR)
        countdown = self._lockout_countdown(canvas, status, button, [entry])

        def check(_event=None):
            if not button.enabled:
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
                    canvas.itemconfig(status, text=f"Wrong master password. {left} attempt{'s' if left != 1 else ''} "
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
            if self.vault.has_recovery_key():
                self.show_menu()
            else:
                self.show_recovery_key("missing")

        button.command = check
        entry.bind("<Return>", check)
        _raise_window(root)
        countdown()

    def _lockout_countdown(self, canvas: Canvas, status: int, button: "_Pill", entries: List[Entry]):
        """Return a function that disables the form while the vault is locked out, ticking every second."""
        def countdown():
            if not entries[0].winfo_exists():
                return
            remaining = self.vault.lockout_remaining()
            if remaining > 0:
                button.set_enabled(False)
                for entry in entries:
                    entry.config(state="disabled")
                canvas.itemconfig(status, fill=MASTER_ERROR,
                                  text=f"Too many failed attempts. Try again in {format_duration(remaining)}.")
                self.root.after(1000, countdown)
            else:
                button.set_enabled(True)
                for entry in entries:
                    entry.config(state="normal")
                canvas.itemconfig(status, text="")
                entries[0].focus_set()
        return countdown

    # -------------------------------------------------------------- recovery key

    def show_recover(self) -> None:
        """Forgot the master password: use the recovery key to set a new one."""
        self._clear()
        root = self.root
        root.title(f"{TITLE}: recover your vault")
        if not self.vault.has_recovery_key():
            canvas = _master_canvas(root, 820, 400, 300, ("master", "shield_key.png"))
            _master_title(root, canvas, 350, 60, "No recovery key")
            _master_text(canvas, 352, 120, "This vault doesn't have a recovery key, so a forgotten master "
                         "password can't be reset. Nobody can decrypt the vault without one of them.\n\n"
                         "If you remember your master password, unlock the vault and the app will help "
                         "you save a recovery key.", width=430)
            _Pill(root, canvas, 445, 320, "Back", self.show_unlock, "pill_green.png")
            return

        canvas = _master_canvas(root, 820, 590, 300, ("master", "shield_key.png"))
        _master_title(root, canvas, 350, 40, "Recover your vault")
        _master_text(canvas, 352, 96, "Enter the recovery key you saved, then choose a new master password.",
                     width=430)
        _master_text(canvas, 352, 150, "Recovery key", width=420, size=-15, fill=MASTER_INK)
        key = _secret_field(root, canvas, 350, 174, masked=False)
        _master_text(canvas, 352, 244, "New master password", width=420, size=-15, fill=MASTER_INK)
        first = _secret_field(root, canvas, 350, 268)
        _master_text(canvas, 352, 338, "Confirm new master password", width=420, size=-15, fill=MASTER_INK)
        second = _secret_field(root, canvas, 350, 362)
        status = _master_text(canvas, 352, 428, f"At least {MIN_MASTER_PASSWORD_LENGTH} characters.",
                              width=430, size=-15)
        button = _Pill(root, canvas, 445, 520, "Reset password", None, "pill_green.png", "pill_off.png")
        _master_link(canvas, 566, 520, "Back to unlock", self.show_unlock)
        countdown = self._lockout_countdown(canvas, status, button, [key, first, second])

        def fail(message: str) -> None:
            canvas.itemconfig(status, text=message, fill=MASTER_ERROR)

        def reset(_event=None):
            if not button.enabled:
                return
            if first.get() != second.get():
                fail("The new passwords don't match.")
                return
            try:
                _busy(root, True)
                self.vault.recover(key.get(), first.get())
            except WrongRecoveryKey as exc:
                if exc.locked_for:
                    countdown()
                else:
                    left = FREE_ATTEMPTS - exc.failed_attempts
                    fail(f"Wrong recovery key. {left} attempt{'s' if left != 1 else ''} left before a "
                         "temporary lockout.")
                return
            except VaultLocked:
                countdown()
                return
            except VaultError as exc:
                fail(str(exc))
                return
            finally:
                _busy(root, False)
            self.show_recovery_key("recovered")

        button.command = reset
        key.bind("<Return>", lambda _e: first.focus_set())
        first.bind("<Return>", lambda _e: second.focus_set())
        second.bind("<Return>", reset)
        _raise_window(root)
        countdown()
        if button.enabled:
            canvas.itemconfig(status, text=f"At least {MIN_MASTER_PASSWORD_LENGTH} characters.", fill=MASTER_MUTED)

    RECOVERY_INTROS = {
        "created": "Your vault is ready. If you ever forget your master password, this key is the only "
                   "way back in.",
        "missing": "Your vault doesn't have a recovery key yet. If you forget your master password, this "
                   "key is the only way back in.",
        "recovered": "Your master password has been changed. Save this new recovery key. Your old one "
                     "keeps working until you do.",
        "replace": "This new key replaces your old recovery key once you save it.",
    }

    def show_recovery_key(self, reason: str) -> None:
        """Show a new recovery key and store it once the user says they've saved it."""
        self._clear()
        root = self.root
        root.title(f"{TITLE}: recovery key")
        key = crypto.new_recovery_key()
        canvas = _master_canvas(root, 820, 500, 300, ("menu", "image_6.png"))
        _master_title(root, canvas, 350, 40, "Save your recovery key", size=-30)
        _master_text(canvas, 352, 92, self.RECOVERY_INTROS[reason] + " Write it down or keep it somewhere "
                     "safe, away from this computer.", width=430)
        canvas.create_image(350, 196, anchor="nw", image=_image(root, "master", "field.png"))
        canvas.create_text(560, 223, text=key, fill=MASTER_INK, font=(MONO, -22, "bold"))
        status = _master_text(canvas, 352, 326, "", width=430, size=-15)

        def copy():
            root.clipboard_clear()
            root.clipboard_append(key)
            canvas.itemconfig(status, text="Copied. Paste it somewhere safe, then clear your clipboard.",
                              fill=MASTER_MUTED)

        def save_file():
            path = filedialog.asksaveasfilename(
                parent=root, title="Save recovery key", initialfile="Password Manager recovery key.txt",
                defaultextension=".txt", filetypes=[("Text file", "*.txt")])
            if not path:
                return
            try:
                Path(path).write_text(
                    f"Password Manager recovery key\nCreated {date.today().isoformat()}\n\n{key}\n\n"
                    "If you forget your master password, click \"Forgot your master password?\" on the\n"
                    "unlock screen and enter this key to set a new one. Keep it private: together with\n"
                    "access to your database, it opens your vault.\n", encoding="utf-8")
            except OSError as exc:
                canvas.itemconfig(status, text=f"Couldn't save the file: {exc}", fill=MASTER_ERROR)
                return
            canvas.itemconfig(status, text=f"Saved to {path}", fill=MASTER_MUTED)

        def saved():
            try:
                _busy(root, True)
                self.vault.set_recovery_key(key)
            except (VaultError, mysql.connector.Error) as exc:
                log.exception("saving the recovery key failed")
                canvas.itemconfig(status, text=f"Couldn't store the recovery key: {exc}", fill=MASTER_ERROR)
                return
            finally:
                _busy(root, False)
            self.show_menu()

        _Pill(root, canvas, 433, 290, "Copy", copy, "pill_blue_small.png")
        _Pill(root, canvas, 617, 290, "Save as file", save_file, "pill_blue_small.png")
        _Pill(root, canvas, 445, 420, "I've saved it", saved, "pill_green.png")
        _master_link(canvas, 566, 420, "Remind me later", self.show_menu)
        _raise_window(root)

    # --------------------------------------------------------------------- menu

    def show_menu(self) -> None:
        self._clear()
        root = self.root
        root.title("Menu")
        canvas = _canvas(root, 981, 500, "#A9CEE9")
        _draw(root, canvas, "menu", MENU_IMAGES)
        _image_button(root, canvas, "menu", "button_1.png", "Add password", self.open_add, (515, 70, 190, 48))
        _image_button(root, canvas, "menu", "button_2.png", "View Password", self.open_view, (515, 163, 190, 48))
        _image_button(root, canvas, "menu", "button_3.png", "Delete Password", self.open_delete, (753, 322, 127, 37))
        link = canvas.create_text(816, 398, text="New recovery key", fill=MASTER_LINK,
                                  font=("Inter", -14, "underline"))
        canvas.tag_bind(link, "<Button-1>", lambda _e: self.show_recovery_key("replace"))
        canvas.tag_bind(link, "<Enter>", lambda _e: canvas.config(cursor="hand2"))
        canvas.tag_bind(link, "<Leave>", lambda _e: canvas.config(cursor=""))

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
        username = Entry(win, borderwidth=3, **WHITE_FIELD)
        username.place(x=100, y=84, width=342, height=47)
        password = Entry(win, borderwidth=3, show="*", **WHITE_FIELD)
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

        _image_button(win, canvas, "add", "button_1.png", "Quit", win.destroy, (314, 359, 181, 41))
        _image_button(win, canvas, "add", "button_2.png", "Submit", add, (560, 136, 179, 40))
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
        _image_button(win, canvas, "view", "button_1.png", "Quit", win.destroy, (800, 520, 164, 36))
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
        entry = Entry(win, borderwidth=3, **WHITE_FIELD)
        entry.place(x=124, y=122, width=452, height=45)
        normal_fg = entry.cget("fg")
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
        _image_button(win, canvas, "delete", "button_1.png", "cancel", win.destroy, (271, 287, 166, 38))
        _image_button(win, canvas, "delete", "button_2.png", "Delete", delete, (271, 224, 166, 38))
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
    _set_app_icon(root)
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
