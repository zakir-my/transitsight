"""Database setup and connection management."""

import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "transitsight.db")


def get_connection():
    """Get a SQLite connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def get_db():
    """Context manager for database sessions."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Create all tables if they don't exist."""
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS routes (
                route_id TEXT PRIMARY KEY,
                route_name TEXT NOT NULL,
                route_type TEXT,
                agency TEXT,
                color TEXT DEFAULT '#2196F3',
                is_active INTEGER DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS stops (
                stop_id TEXT PRIMARY KEY,
                stop_name TEXT NOT NULL,
                stop_lat REAL,
                stop_lon REAL
            );

            CREATE TABLE IF NOT EXISTS route_stops (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                route_id TEXT NOT NULL REFERENCES routes(route_id),
                stop_id TEXT NOT NULL REFERENCES stops(stop_id),
                stop_sequence INTEGER
            );

            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                route_id TEXT NOT NULL REFERENCES routes(route_id),
                crowd_level TEXT NOT NULL CHECK(crowd_level IN ('Low', 'Medium', 'Full')),
                confidence REAL,
                time_context TEXT NOT NULL,
                day_context TEXT NOT NULL,
                weather_context TEXT,
                temperature REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                route_id TEXT NOT NULL REFERENCES routes(route_id),
                user_id TEXT DEFAULT 'anonymous',
                predicted_level TEXT NOT NULL,
                reported_level TEXT NOT NULL,
                comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                name TEXT,
                email TEXT,
                role TEXT DEFAULT 'commuter' CHECK(role IN ('commuter', 'authority', 'admin')),
                feedback_count INTEGER DEFAULT 0,
                streak INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS api_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service TEXT NOT NULL,
                endpoint TEXT,
                status TEXT,
                response_time_ms INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS system_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- Insert default admin user
            INSERT OR IGNORE INTO users (user_id, name, email, role)
            VALUES ('admin', 'Admin', 'admin@transitsight.my', 'admin');
        """)


def log_api_call(service: str, endpoint: str = "", status: str = "success",
                 response_time_ms: int = 0):
    """Record an external API call in the audit log."""
    try:
        with get_db() as conn:
            conn.execute(
                """INSERT INTO api_log (service, endpoint, status, response_time_ms)
                   VALUES (?, ?, ?, ?)""",
                (service, endpoint, status, response_time_ms),
            )
    except Exception:
        pass  # Audit logging must never break the main flow
