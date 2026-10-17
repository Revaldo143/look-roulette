"""SQLite storage for Look Roulette: spin history + taste profile."""
import json
import os
import sqlite3
from datetime import datetime, timezone

DB_PATH = os.environ.get(
    "LOOKROULETTE_DB",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "lookroulette.db"),
)


def _connect():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _connect()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS spins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            look_name TEXT NOT NULL,
            family TEXT NOT NULL,
            texture TEXT NOT NULL,
            lip_hex TEXT NOT NULL,
            blush_hex TEXT NOT NULL,
            shadows_json TEXT NOT NULL,
            intensity INTEGER NOT NULL,
            jackpot INTEGER NOT NULL DEFAULT 0,
            liked INTEGER,
            mock INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS taste (
            family TEXT NOT NULL,
            texture TEXT NOT NULL,
            likes INTEGER NOT NULL DEFAULT 0,
            dislikes INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (family, texture)
        );
        """
    )
    conn.commit()
    conn.close()


def save_spin(palette, jackpot, mock):
    conn = _connect()
    cur = conn.execute(
        """INSERT INTO spins
           (created_at, look_name, family, texture, lip_hex, blush_hex,
            shadows_json, intensity, jackpot, mock)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            datetime.now(timezone.utc).isoformat(),
            palette["look_name"],
            palette["family"],
            palette["texture"],
            palette["lip"]["hex"],
            palette["blush_hex"],
            json.dumps(palette["shadows"]),
            palette["intensity"],
            1 if jackpot else 0,
            1 if mock else 0,
        ),
    )
    spin_id = cur.lastrowid
    conn.commit()
    conn.close()
    return spin_id


def get_spin(spin_id):
    conn = _connect()
    row = conn.execute("SELECT * FROM spins WHERE id = ?", (spin_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def set_swipe(spin_id, liked):
    """Record a like/dislike; updates the taste profile for that family+texture."""
    spin = get_spin(spin_id)
    if not spin:
        return False
    conn = _connect()
    conn.execute("UPDATE spins SET liked = ? WHERE id = ?", (1 if liked else 0, spin_id))
    conn.execute(
        """INSERT INTO taste (family, texture, likes, dislikes)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(family, texture) DO UPDATE SET
             likes = likes + excluded.likes,
             dislikes = dislikes + excluded.dislikes""",
        (spin["family"], spin["texture"], 1 if liked else 0, 0 if liked else 1),
    )
    conn.commit()
    conn.close()
    return True


def get_taste_weights():
    """Return {(family, texture): (likes, dislikes)} for the palette generator."""
    conn = _connect()
    rows = conn.execute("SELECT family, texture, likes, dislikes FROM taste").fetchall()
    conn.close()
    return {(r["family"], r["texture"]): (r["likes"], r["dislikes"]) for r in rows}


def list_spins(limit=20):
    conn = _connect()
    rows = conn.execute(
        "SELECT id, created_at, look_name, family, texture, lip_hex, liked, jackpot, mock"
        " FROM spins ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def spin_count():
    conn = _connect()
    n = conn.execute("SELECT COUNT(*) AS c FROM spins").fetchone()["c"]
    conn.close()
    return n


def style_iq():
    """Overall like ratio across all swipes. Returns (likes, dislikes, pct_or_None)."""
    conn = _connect()
    row = conn.execute(
        "SELECT COALESCE(SUM(likes),0) AS l, COALESCE(SUM(dislikes),0) AS d FROM taste"
    ).fetchone()
    conn.close()
    likes, dislikes = row["l"], row["d"]
    total = likes + dislikes
    pct = round(100 * likes / total) if total else None
    return likes, dislikes, pct
