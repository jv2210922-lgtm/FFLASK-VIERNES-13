import sqlite3

from flask import current_app, g


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
        g.db.execute("PRAGMA journal_mode = WAL")
    return g.db


def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS plazas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            address TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            description TEXT,
            photo TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tracking_code TEXT NOT NULL UNIQUE,
            citizen_name TEXT,
            email TEXT,
            plaza_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            photo TEXT,
            reported_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pendiente'
                CHECK (status IN ('Pendiente', 'En revisión', 'En proceso', 'Solucionado')),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (plaza_id) REFERENCES plazas(id) ON DELETE RESTRICT
        );
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_reports_plaza ON reports(plaza_id);
        CREATE INDEX IF NOT EXISTS idx_reports_status ON reports(status);
        CREATE INDEX IF NOT EXISTS idx_reports_tracking ON reports(tracking_code);
        """
    )
    db.commit()


def init_app(app):
    app.teardown_appcontext(close_db)
