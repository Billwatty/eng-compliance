from __future__ import annotations

import os
import sqlite3
import stat
from pathlib import Path

import pytest

from app.db import connect
from app.ledger import FileVault, Ledger


@pytest.fixture
def conn(tmp_path: Path) -> sqlite3.Connection:
    c = connect(tmp_path / "t.db")
    yield c
    c.close()


@pytest.fixture
def ledger(conn) -> Ledger:
    return Ledger(conn)


@pytest.fixture
def vault(tmp_path: Path) -> FileVault:
    v = FileVault(tmp_path / "vault")
    yield v
    for p in (tmp_path / "vault").rglob("*"):
        if p.is_file():
            os.chmod(p, stat.S_IWUSR | stat.S_IRUSR)


@pytest.fixture
def demo(conn):
    from app.demo import seed
    return seed(conn)
