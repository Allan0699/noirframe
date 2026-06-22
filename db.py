"""
Lightweight SQLite data layer.

No ORM is used -- just sqlite3 with row factories so query results behave
like dictionaries in templates and route handlers. Keeping this dependency
-free (stdlib only) means the whole project runs with nothing more than
Flask + python-dotenv + requests installed.
"""

import sqlite3
from flask import current_app, g


def get_db():
    """Return a SQLite connection for the current request, creating it once."""
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE_PATH"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app):
    """Create tables if they don't exist yet. Safe to call on every boot."""
    with app.app_context():
        db = get_db()
        with open(app.config["SCHEMA_PATH"], "r") as f:
            db.executescript(f.read())
        db.commit()


def query_all(sql, params=()):
    return get_db().execute(sql, params).fetchall()


def query_one(sql, params=()):
    return get_db().execute(sql, params).fetchone()


def execute(sql, params=()):
    """INSERT/UPDATE/DELETE helper. Returns the lastrowid (for inserts)."""
    db = get_db()
    cur = db.execute(sql, params)
    db.commit()
    return cur.lastrowid


def register_db(app):
    app.teardown_appcontext(close_db)
