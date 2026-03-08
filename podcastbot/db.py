"""
SQLite storage for articles and digest tracking.
"""

import sqlite3
import time
from datetime import datetime

from podcastbot.config import DB_PATH


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = _connect()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL UNIQUE,
            title TEXT,
            summary TEXT,
            source_domain TEXT,
            submitted_at INTEGER,
            week_id TEXT,
            digest_included INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS digests (
            week_id TEXT PRIMARY KEY,
            content TEXT,
            article_count INTEGER,
            created_at INTEGER
        );
        CREATE INDEX IF NOT EXISTS idx_articles_week ON articles(week_id);
    """)
    conn.commit()
    conn.close()


def current_week_id() -> str:
    return datetime.now().strftime("%Y-W%W")


def add_article(url: str, title: str | None = None, summary: str | None = None,
                source_domain: str | None = None) -> bool:
    conn = _connect()
    try:
        conn.execute("""
            INSERT INTO articles (url, title, summary, source_domain, submitted_at, week_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (url, title, summary, source_domain, int(time.time()), current_week_id()))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def update_article(url: str, title: str, summary: str, source_domain: str):
    conn = _connect()
    conn.execute("""
        UPDATE articles SET title=?, summary=?, source_domain=?
        WHERE url=?
    """, (title, summary, source_domain, url))
    conn.commit()
    conn.close()


def get_week_articles(week_id: str | None = None) -> list[dict]:
    conn = _connect()
    wid = week_id or current_week_id()
    rows = conn.execute(
        "SELECT * FROM articles WHERE week_id=? ORDER BY submitted_at",
        (wid,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_digested(week_id: str, content: str, count: int):
    conn = _connect()
    conn.execute("""
        INSERT INTO digests (week_id, content, article_count, created_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(week_id) DO UPDATE SET content=excluded.content,
            article_count=excluded.article_count, created_at=excluded.created_at
    """, (week_id, content, count, int(time.time())))
    conn.execute("UPDATE articles SET digest_included=1 WHERE week_id=?", (week_id,))
    conn.commit()
    conn.close()


def get_article_count(week_id: str | None = None) -> int:
    conn = _connect()
    wid = week_id or current_week_id()
    row = conn.execute("SELECT COUNT(*) as c FROM articles WHERE week_id=?", (wid,)).fetchone()
    conn.close()
    return row["c"]
