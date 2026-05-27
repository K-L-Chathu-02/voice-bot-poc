import os
import sqlite3
from contextlib import contextmanager

from . import schema

_CONN: sqlite3.Connection | None = None


def get_conn() -> sqlite3.Connection:
    global _CONN
    if _CONN is None:
        path = os.environ.get("SLT_DB_PATH", "./slt_mock_data.db")
        _CONN = sqlite3.connect(path, check_same_thread=False)
        _CONN.row_factory = sqlite3.Row
        _CONN.execute("PRAGMA foreign_keys = ON")
    return _CONN


@contextmanager
def cursor():
    conn = get_conn()
    cur = conn.cursor()
    try:
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()


def bootstrap() -> None:
    schema.apply(get_conn())
