"""
Phase 7 — test isolation helpers.

Shared by ``conftest.py`` and ``tests/test_isolation.py``. Kept separate from
the app modules so the plain standalone runners (``python -m tests.test_*``)
and the pytest stack use the same well-defined temp-file semantics.
"""
import os
import shutil
import tempfile


def sqlite_file_path(url: str) -> str:
    """Return the filesystem path from a sqlite(+driver):// URL."""
    if ":///" in url:
        return url.split(":///", 1)[1]
    return url.split("://", 1)[1]


def make_test_url() -> tuple[str, str]:
    """Create a fresh temp directory and return (TEST_DATABASE_URL, root).

    The returned URL is normalized to forward slashes so it works as both a
    SQLAlchemy URL and a plain filesystem path.
    """
    root = tempfile.mkdtemp(prefix="flight_test_").replace("\\", "/")
    url = f"sqlite+aiosqlite:///{root}/test.db"
    return url, root


def cleanup_db_files(primary_path: str) -> None:
    """Delete an SQLite file plus its -wal/-shm sidecars, ignoring missing."""
    for path in (primary_path, primary_path + "-wal", primary_path + "-shm"):
        try:
            os.remove(path)
        except FileNotFoundError:
            pass


def cleanup_temp_dir(root: str) -> None:
    """Recursively remove a temp dir used for an isolated test DB."""
    shutil.rmtree(root, ignore_errors=True)