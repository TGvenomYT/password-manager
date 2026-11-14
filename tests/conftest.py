"""Test fixtures.

Database tests need a disposable MySQL/MariaDB server, given as
PM_TEST_MYSQL="user:password@host:port" (the password may be empty). Each test
gets its own throwaway database. Tests are skipped when the variable is unset.
"""

from __future__ import annotations

import os
import uuid

import pytest

from password_manager import crypto


def _parse(url: str):
    creds, _, hostport = url.rpartition("@")
    user, _, password = creds.partition(":")
    host, _, port = hostport.partition(":")
    return dict(user=user, password=password, host=host or "127.0.0.1", port=int(port or 3306))


@pytest.fixture
def mysql_admin():
    url = os.environ.get("PM_TEST_MYSQL")
    if not url:
        pytest.skip("set PM_TEST_MYSQL=user:password@host:port to run database tests")
    import mysql.connector

    return lambda **extra: mysql.connector.connect(**_parse(url), **extra)


@pytest.fixture
def conn(mysql_admin):
    name = f"pm_test_{uuid.uuid4().hex[:10]}"
    admin = mysql_admin()
    admin.cursor().execute(f"CREATE DATABASE `{name}`")
    connection = mysql_admin(database=name, autocommit=False)
    yield connection
    connection.close()
    admin.cursor().execute(f"DROP DATABASE `{name}`")
    admin.close()


@pytest.fixture
def fast_kdf():
    """Cheap scrypt parameters so the tests run quickly (production uses n=2**17)."""
    return lambda: crypto.KdfParams(salt=os.urandom(16), n=2**10, r=8, p=1)


class FakeClock:
    def __init__(self, now: float = 1_000_000.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def clock():
    return FakeClock()
