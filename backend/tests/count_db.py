"""
Phase 7 — inspect SQLite database counts (read-only).

Used by the verification harness to prove the dev/production database is
untouched before and after the isolated test run. Never imports app modules,
never writes, and opens the file read-only (mode=ro), so it cannot modify the
database or create/mutate WAL sidecars.
"""
import json
import sqlite3
import sys


def main(db_path: str) -> None:
    tables = ("flights", "users", "bookings", "passengers", "payments")
    demo_emails = ("bilal@example.com", "sara@example.com", "guest@example.com")

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        present = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}
        counts = {
            t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            for t in tables if t in present
        }
        counts.setdefault("alembic", None)
        if "alembic_version" in present:
            row = conn.execute("SELECT version_num FROM alembic_version").fetchone()
            counts["alembic"] = row[0] if row else None
        counts["demo_users"] = 0
        if "users" in present:
            counts["demo_users"] = conn.execute(
                "SELECT COUNT(*) FROM users WHERE email IN (?,?,?)", demo_emails
            ).fetchone()[0]
        counts["ek601"] = None
        if "flights" in present:
            row = conn.execute(
                "SELECT flight_number, available_seats, base_price FROM flights "
                "WHERE flight_number=?",
                ("EK-601",),
            ).fetchone()
            if row:
                counts["ek601"] = {"flight_number": row[0], "available_seats": row[1], "base_price": row[2]}
    finally:
        conn.close()

    print(json.dumps(counts, sort_keys=True))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python tests/count_db.py <sqlite-file>", file=sys.stderr)
        sys.exit(2)
    main(sys.argv[1])