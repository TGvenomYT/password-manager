"""`password_manager erase`: what the uninstallers run to erase what isn't a file."""

import os
import uuid

import pytest

from password_manager import alerts, erase_cli, setup_cli
from password_manager import config as cfgmod
from password_manager import prefs as prefsmod



class FakeKeyring:
    def __init__(self, fail=False):
        self.store, self.fail = {}, fail

    def get_password(self, service, user):
        if self.fail:
            raise RuntimeError("password store is locked")
        return self.store.get((service, user))

    def delete_password(self, service, user):
        del self.store[(service, user)]


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("PASSWORD_MANAGER_HOME", str(tmp_path))
    return tmp_path


def test_drop_sql_only_takes_plain_names():
    assert erase_cli.drop_sql("password_manager", "pm_app") == [
        "DROP DATABASE IF EXISTS `password_manager`", "DROP USER IF EXISTS 'pm_app'@'localhost'"]
    with pytest.raises(cfgmod.ConfigError):
        erase_cli.drop_sql("x`; DROP DATABASE mysql; --", "pm_app")


def test_removes_the_alerts_app_password(home, monkeypatch, capsys):
    store = FakeKeyring()
    store.store[(alerts.KEYRING_SERVICE, "alex@gmail.com")] = "abcdefghijklmnop"
    monkeypatch.setattr(alerts, "_keyring", lambda: store)
    prefsmod.save(prefsmod.Prefs(alert_email="alex@gmail.com", email_alerts=True))
    assert erase_cli.main(["--keep-database"]) == 0
    assert store.store == {}
    assert "Removed the app password for email alerts (alex@gmail.com)" in capsys.readouterr().out
    assert erase_cli.main(["--keep-database"]) == 0  # nothing left: still fine


def test_says_so_when_the_password_store_fails(home, monkeypatch, capsys):
    monkeypatch.setattr(alerts, "_keyring", lambda: FakeKeyring(fail=True))
    prefsmod.save(prefsmod.Prefs(alert_email="alex@gmail.com"))
    assert erase_cli.main(["--keep-database"]) == 1
    assert "Couldn't remove the app password" in capsys.readouterr().out


def test_nothing_to_drop_without_settings(home, capsys):
    assert erase_cli.main([]) == 0
    assert "no vault database to remove" in capsys.readouterr().out


def test_drops_the_vault_database_and_user(home, mysql_admin, monkeypatch, capsys):
    creds, _, hostport = os.environ["PM_TEST_MYSQL"].rpartition("@")
    user, _, password = creds.partition(":")
    host, _, port = hostport.partition(":")
    url = dict(user=user, password=password, host=host or "127.0.0.1", port=int(port or 3306))
    name = f"pm_erase_{uuid.uuid4().hex[:8]}"
    admin = mysql_admin()
    cur = admin.cursor()
    for statement in setup_cli.provisioning_sql(name, name, "x" * 20):
        cur.execute(statement)
    dbc = cfgmod.DbConfig(host=url["host"], port=url["port"], user=name, database=name)
    cfgmod.save(cfgmod.Config(db=dbc, gpg_binary="gpg"))
    # The admin login: no password first, then it asks, as it would in a terminal.
    monkeypatch.setattr(setup_cli.getpass, "getpass", lambda prompt="": url["password"])
    assert erase_cli.main(["--admin-user", url["user"]]) == 0
    assert f"Removed the vault database '{name}'" in capsys.readouterr().out
    cur.execute("SELECT COUNT(*) FROM information_schema.SCHEMATA WHERE SCHEMA_NAME = %s", (name,))
    assert cur.fetchone()[0] == 0
    cur.execute("SELECT COUNT(*) FROM mysql.user WHERE user = %s", (name,))
    assert cur.fetchone()[0] == 0
    admin.close()


def test_explains_how_to_drop_it_by_hand_when_it_cant(home, monkeypatch, capsys):
    dbc = cfgmod.DbConfig(host="127.0.0.1", port=1, user="pm_app", database="password_manager")  # nothing there
    cfgmod.save(cfgmod.Config(db=dbc, gpg_binary="gpg"))
    assert erase_cli.main([]) == 1
    out = capsys.readouterr().out
    assert "DROP DATABASE IF EXISTS `password_manager`;" in out and "DROP USER IF EXISTS 'pm_app'@'localhost';" in out
