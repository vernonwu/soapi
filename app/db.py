import sqlite3
from datetime import datetime
from pathlib import Path

PRAGMAS = [
    "PRAGMA busy_timeout = 5000",
    "PRAGMA journal_mode = WAL",
    "PRAGMA synchronous = NORMAL",
    "PRAGMA foreign_keys = ON",
]


def connect(db_path: str):
    # autocommit; context managers still work
    conn = sqlite3.connect(db_path, timeout=10.0, isolation_level=None)
    conn.row_factory = sqlite3.Row
    for p in PRAGMAS:
        conn.execute(p)
    return conn


def ensure_schema(db_path: str):
    p = Path(__file__).with_name("schema.sql")
    schema = p.read_text(encoding="utf-8")

    with connect(db_path) as c:
        # run base schema
        for stmt in [s.strip() for s in schema.split(";") if s.strip()]:
            c.execute(stmt)

        # migrations: add columns if missing
        def cols(table):
            return {r["name"] for r in c.execute(f"PRAGMA table_info({table})")}

        mcols = cols("machine")
        if "max_concurrent" not in mcols:
            c.execute(
                "ALTER TABLE machine ADD COLUMN max_concurrent INTEGER NOT NULL DEFAULT 1"
            )

        rcols = cols("reservation")
        if "front_since_ts" not in rcols:
            c.execute("ALTER TABLE reservation ADD COLUMN front_since_ts TEXT")
        if "remarks" not in rcols:
            c.execute("ALTER TABLE reservation ADD COLUMN remarks TEXT")

        lgcols = cols("op_log")
        if "machine" not in lgcols:
            c.execute("ALTER TABLE op_log ADD COLUMN machine TEXT")


def log_op_tx(conn, user: str, op: str, machine: str, detail: str):
    conn.execute(
        "INSERT INTO op_log(ts,user,machine,op,detail) VALUES(?,?,?,?,?)",
        (datetime.now().isoformat(timespec="seconds"), user, machine, op, detail),
    )

