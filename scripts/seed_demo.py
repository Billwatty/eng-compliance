"""Load the demo contract. Usage: python -m scripts.seed_demo [--reset]"""
from __future__ import annotations

import os
import shutil
import stat
import sys

from app.config import load_settings
from app.db import connect, row
from app.demo import seed


def _force_remove(func, path, _exc):
    os.chmod(path, stat.S_IWUSR | stat.S_IRUSR)
    func(path)


def main() -> None:
    settings = load_settings()
    if "--reset" in sys.argv and settings.data_dir.exists():
        shutil.rmtree(settings.data_dir, onerror=_force_remove)
    conn = connect(settings.db_path)
    if row(conn, "SELECT id FROM contracts LIMIT 1"):
        print("A contract already exists. Run with --reset to replace all data with the demo.")
        return
    seed(conn)
    print(f"Demo contract loaded into {settings.db_path}")


if __name__ == "__main__":
    main()
