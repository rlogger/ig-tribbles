import aiosqlite
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

# Use environment variable or default to local path
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", Path(__file__).parent / "follower_data.db"))


async def init_db():
    """Initialize the database with required tables."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Store each CSV upload as a snapshot
        await db.execute("""
            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                guild_id INTEGER NOT NULL,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                filename TEXT,
                total_followers INTEGER DEFAULT 0,
                total_following INTEGER DEFAULT 0,
                snapshot_type TEXT DEFAULT 'followers'
            )
        """)

        # Store individual follower/following records per snapshot
        await db.execute("""
            CREATE TABLE IF NOT EXISTS records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_id INTEGER NOT NULL,
                ig_user_id TEXT,
                username TEXT NOT NULL,
                fullname TEXT,
                followed_by_you TEXT,
                is_verified TEXT,
                profile_url TEXT,
                record_type TEXT DEFAULT 'follower',
                FOREIGN KEY (snapshot_id) REFERENCES snapshots(id)
            )
        """)

        # Index for faster queries
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_records_snapshot
            ON records(snapshot_id)
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_records_username
            ON records(username)
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_snapshots_user
            ON snapshots(user_id, guild_id)
        """)

        await db.commit()


async def save_snapshot(
    user_id: int,
    guild_id: int,
    filename: str,
    records: list[dict],
    snapshot_type: str = "followers"
) -> int:
    """Save a new snapshot and return its ID."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO snapshots (user_id, guild_id, filename, total_followers, snapshot_type)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, guild_id, filename, len(records), snapshot_type)
        )
        snapshot_id = cursor.lastrowid

        # Insert all records
        for record in records:
            await db.execute(
                """
                INSERT INTO records (
                    snapshot_id, ig_user_id, username, fullname,
                    followed_by_you, is_verified, profile_url, record_type
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot_id,
                    record.get("user_id", ""),
                    record.get("username", ""),
                    record.get("fullname", ""),
                    record.get("followed_by_you", ""),
                    record.get("is_verified", ""),
                    record.get("profile_url", ""),
                    snapshot_type
                )
            )

        await db.commit()
        return snapshot_id


async def get_snapshots(user_id: int, guild_id: int, limit: int = 10) -> list[dict]:
    """Get recent snapshots for a user."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT * FROM snapshots
            WHERE user_id = ? AND guild_id = ?
            ORDER BY uploaded_at DESC
            LIMIT ?
            """,
            (user_id, guild_id, limit)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_snapshot_records(snapshot_id: int) -> list[dict]:
    """Get all records for a snapshot."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT * FROM records WHERE snapshot_id = ?
            """,
            (snapshot_id,)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_latest_snapshot(
    user_id: int,
    guild_id: int,
    snapshot_type: str = "followers"
) -> Optional[dict]:
    """Get the most recent snapshot of a specific type."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT * FROM snapshots
            WHERE user_id = ? AND guild_id = ? AND snapshot_type = ?
            ORDER BY uploaded_at DESC
            LIMIT 1
            """,
            (user_id, guild_id, snapshot_type)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_all_snapshots_for_plotting(
    user_id: int,
    guild_id: int
) -> list[dict]:
    """Get all snapshots for plotting trends."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT id, uploaded_at, total_followers, snapshot_type
            FROM snapshots
            WHERE user_id = ? AND guild_id = ?
            ORDER BY uploaded_at ASC
            """,
            (user_id, guild_id)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def compare_snapshots(old_snapshot_id: int, new_snapshot_id: int) -> dict:
    """Compare two snapshots and return differences."""
    old_records = await get_snapshot_records(old_snapshot_id)
    new_records = await get_snapshot_records(new_snapshot_id)

    old_usernames = {r["username"] for r in old_records}
    new_usernames = {r["username"] for r in new_records}

    gained = new_usernames - old_usernames
    lost = old_usernames - new_usernames

    # Get full details for gained/lost
    gained_details = [r for r in new_records if r["username"] in gained]
    lost_details = [r for r in old_records if r["username"] in lost]

    return {
        "gained": gained_details,
        "lost": lost_details,
        "gained_count": len(gained),
        "lost_count": len(lost),
        "old_total": len(old_records),
        "new_total": len(new_records),
        "net_change": len(new_records) - len(old_records)
    }
