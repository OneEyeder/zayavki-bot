"""SQLite database module for storing applications."""
import sqlite3
import os
from typing import List, Optional, Dict
from dataclasses import dataclass


@dataclass
class Application:
    app_id: int
    created_at: int
    user_id: int
    username: str
    comment: str
    status: str = "new"


# Для Render.com используем /app/data или текущую директорию
DB_DIR = os.getenv("DATA_DIR", os.path.dirname(__file__))
DB_PATH = os.path.join(DB_DIR, "applications.db")


def init_db() -> None:
    """Initialize database with applications table."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            username TEXT,
            comment TEXT NOT NULL,
            status TEXT DEFAULT 'new'
        )
    """)
    conn.commit()
    conn.close()


def create_application(user_id: int, username: str, comment: str) -> Application:
    """Create new application in database."""
    created_at = int(__import__('time').time())
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO applications (created_at, user_id, username, comment, status) VALUES (?, ?, ?, ?, ?)",
        (created_at, user_id, username, comment, "new")
    )
    app_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return Application(
        app_id=app_id,
        created_at=created_at,
        user_id=user_id,
        username=username,
        comment=comment,
        status="new"
    )


def get_application(app_id: int) -> Optional[Application]:
    """Get single application by ID."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM applications WHERE id = ?", (app_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return Application(
            app_id=row[0],
            created_at=row[1],
            user_id=row[2],
            username=row[3] or "",
            comment=row[4],
            status=row[5]
        )
    return None


def get_recent_applications(limit: int = 10) -> List[Application]:
    """Get recent applications ordered by ID descending."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM applications ORDER BY id DESC LIMIT ?",
        (limit,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        Application(
            app_id=row[0],
            created_at=row[1],
            user_id=row[2],
            username=row[3] or "",
            comment=row[4],
            status=row[5]
        )
        for row in rows
    ]


def update_application_status(app_id: int, status: str) -> bool:
    """Update application status."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE applications SET status = ? WHERE id = ?",
        (status, app_id)
    )
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return updated


def get_all_applications() -> List[Application]:
    """Get all applications ordered by ID."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM applications ORDER BY id")
    rows = cursor.fetchall()
    conn.close()
    return [
        Application(
            app_id=row[0],
            created_at=row[1],
            user_id=row[2],
            username=row[3] or "",
            comment=row[4],
            status=row[5]
        )
        for row in rows
    ]


def get_applications_by_user(user_id: int) -> List[Application]:
    """Get all applications for specific user."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM applications WHERE user_id = ? ORDER BY id", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [
        Application(
            app_id=row[0],
            created_at=row[1],
            user_id=row[2],
            username=row[3] or "",
            comment=row[4],
            status=row[5]
        )
        for row in rows
    ]


def get_next_app_id() -> int:
    """Get next application ID (max + 1)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(id) FROM applications")
    result = cursor.fetchone()
    conn.close()
    return (result[0] or 0) + 1
