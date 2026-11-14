"""MySQL connections."""

from __future__ import annotations

import mysql.connector

from .config import DbConfig


def connect(db: DbConfig, password: str, *, with_database: bool = True):
    """Connect as the app user and select the vault database, creating it if needed.

    No ``auth_plugin`` is forced. The old ``mysql_native_password`` setting
    breaks on MySQL 9, where that plugin was removed, so the server negotiates
    instead (caching_sha2_password on MySQL 8+/9, native on MariaDB).
    """
    kwargs = dict(
        user=db.user,
        password=password,
        autocommit=False,
        connection_timeout=10,
        charset="utf8mb4",
        use_unicode=True,
    )
    if db.unix_socket:
        kwargs["unix_socket"] = db.unix_socket
    else:
        kwargs.update(host=db.host, port=db.port)
    conn = mysql.connector.connect(**kwargs)
    if with_database:
        cur = conn.cursor()
        cur.execute(f"CREATE DATABASE IF NOT EXISTS `{db.database}` CHARACTER SET utf8mb4")
        cur.execute(f"USE `{db.database}`")
        cur.close()
    return conn
