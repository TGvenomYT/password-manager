"""Every screen of the Qt interface loads without QML errors (off-screen, no database needed)."""

import os

import pytest

pytest.importorskip("PySide6.QtGui", reason="PySide6 isn't installed")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_every_screen_loads():
    from password_manager.app import self_test_ui

    assert self_test_ui() == []


def test_the_app_icon_is_bundled_at_every_size():
    from PySide6.QtGui import QImage

    from password_manager.app import ICON_FILES, WINDOW_ICON_SIZES, app_icon, make_app

    for path in ICON_FILES:
        assert path.is_file(), path
    make_app(["password-manager"])
    sizes = [s.width() for s in app_icon().availableSizes()]
    assert sizes == [*WINDOW_ICON_SIZES, 512]
    # The in-app icon's three layers are the same size as the full icon they stack into.
    layers = [QImage(str(p)) for p in ICON_FILES[1:4]]
    assert {(i.width(), i.height()) for i in layers} == {(512, 512)}


def test_the_interface_never_receives_a_password(tmp_path, monkeypatch):
    """Passwords are never shown: the details the screens read hold none, and copying goes straight
    from the backend to the clipboard."""
    from PySide6.QtGui import QGuiApplication

    from password_manager import config as cfgmod
    from password_manager.app import make_app
    from password_manager.backend import Backend
    from password_manager.vault import Entry

    make_app(["password-manager"])
    monkeypatch.setattr(cfgmod, "config_dir", lambda: tmp_path)
    backend = Backend()
    try:
        entry = Entry(id=7, username="alex", password="S3cret-Pa55!", title="GitHub",
                      history=({"password": "Old-Pa55!", "changed": 1.0},))
        backend._active = [entry]
        backend._selected_id = 7
        backend._update_selected()
        shown = repr(backend.selected)
        assert "S3cret-Pa55!" not in shown and "Old-Pa55!" not in shown
        assert backend.selected["hasPassword"] and len(backend.selected["history"]) == 1
        assert backend.passwordFor(7) == "S3cret-Pa55!" and backend.passwordFor(99) == ""

        clipboard = QGuiApplication.clipboard()
        backend.copyField("password")
        assert clipboard.text() == "S3cret-Pa55!"
        backend.copyHistory(0)
        assert clipboard.text() == "Old-Pa55!"
        backend.copyPassword("typed-in-the-editor")
        assert clipboard.text() == "typed-in-the-editor"
        assert backend._clip_timer.isActive()  # and it clears itself
    finally:
        backend.shutdown()
