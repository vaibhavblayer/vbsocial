"""SQLite database for post tracking."""

import json
import sqlite3
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional
import uuid


class PostStatus(str, Enum):
    """Post status values."""
    DRAFT = "draft"
    READY = "ready"
    POSTING = "posting"  # Currently being posted
    POSTED = "posted"
    FAILED = "failed"  # Posting failed


def generate_short_uuid(length: int = 6) -> str:
    """Generate a short UUID (6-8 chars)."""
    return uuid.uuid4().hex[:length]


class PostDB:
    """SQLite database manager for posts."""
    
    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS posts (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'draft',
                    scheduled_for TEXT,
                    folder_path TEXT NOT NULL,
                    source_type TEXT,
                    source_file TEXT,
                    title TEXT,
                    post_ids TEXT,
                    last_error TEXT,
                    posted_at TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_status ON posts(status)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_scheduled ON posts(scheduled_for)
            """)
            conn.commit()
    
    def create_post(
        self,
        folder_path: str,
        source_type: str | None = None,
        source_file: str | None = None,
        title: str | None = None,
        post_id: str | None = None,
    ) -> str:
        """Create a new post entry. Returns the UUID."""
        post_id = post_id or generate_short_uuid()
        now = datetime.now().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO posts (id, created_at, updated_at, status, folder_path, source_type, source_file, title)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (post_id, now, now, PostStatus.DRAFT.value, folder_path, source_type, source_file, title),
            )
            conn.commit()
        
        return post_id
    
    def get_post(self, post_id: str) -> dict | None:
        """Get a post by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None
    
    def update_status(self, post_id: str, status: PostStatus) -> bool:
        """Update post status."""
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "UPDATE posts SET status = ?, updated_at = ? WHERE id = ?",
                (status.value, now, post_id),
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def update_folder_path(self, post_id: str, folder_path: str) -> bool:
        """Update post folder path."""
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "UPDATE posts SET folder_path = ?, updated_at = ? WHERE id = ?",
                (folder_path, now, post_id),
            )
            conn.commit()
            return cursor.rowcount > 0

    def schedule_post(self, post_id: str, scheduled_for: datetime | str) -> bool:
        """Schedule a post for a specific date."""
        if isinstance(scheduled_for, datetime):
            scheduled_for = scheduled_for.isoformat()
        
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "UPDATE posts SET scheduled_for = ?, updated_at = ? WHERE id = ? AND status = ?",
                (scheduled_for, now, post_id, PostStatus.READY.value),
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def unschedule_post(self, post_id: str) -> bool:
        """Remove schedule from a post."""
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "UPDATE posts SET scheduled_for = NULL, updated_at = ? WHERE id = ?",
                (now, post_id),
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def save_post_ids(self, post_id: str, platform_ids: dict) -> bool:
        """Save platform post IDs after posting."""
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "UPDATE posts SET post_ids = ?, updated_at = ? WHERE id = ?",
                (json.dumps(platform_ids), now, post_id),
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def list_posts(
        self,
        status: PostStatus | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """List posts, optionally filtered by status."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            if status:
                cursor = conn.execute(
                    "SELECT * FROM posts WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                    (status.value, limit),
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM posts ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                )
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_scheduled_posts(self, before: datetime | None = None) -> list[dict]:
        """Get posts scheduled for posting."""
        before = before or datetime.now()
        before_str = before.isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM posts 
                WHERE status = ? AND scheduled_for IS NOT NULL AND scheduled_for <= ?
                ORDER BY scheduled_for ASC
                """,
                (PostStatus.READY.value, before_str),
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def count_by_status(self) -> dict[str, int]:
        """Get count of posts by status."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT status, COUNT(*) as count FROM posts GROUP BY status"
            )
            return {row[0]: row[1] for row in cursor.fetchall()}
    
    def delete_post(self, post_id: str) -> bool:
        """Delete a post from database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM posts WHERE id = ?", (post_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def find_by_folder(self, folder_path: str) -> dict | None:
        """Find post by folder path."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM posts WHERE folder_path = ?", (folder_path,)
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None

    def mark_posting(self, post_id: str) -> bool:
        """Mark post as currently being posted."""
        return self.update_status(post_id, PostStatus.POSTING)
    
    def mark_posted(self, post_id: str, platform_ids: dict) -> bool:
        """Mark post as successfully posted."""
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                UPDATE posts 
                SET status = ?, post_ids = ?, posted_at = ?, last_error = NULL, updated_at = ?
                WHERE id = ?
                """,
                (PostStatus.POSTED.value, json.dumps(platform_ids), now, now, post_id),
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def mark_failed(self, post_id: str, error: str) -> bool:
        """Mark post as failed with error message."""
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                UPDATE posts 
                SET status = ?, last_error = ?, updated_at = ?
                WHERE id = ?
                """,
                (PostStatus.FAILED.value, error, now, post_id),
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def get_due_posts(self) -> list[dict]:
        """Get posts that are due for posting (scheduled_for <= now and status = ready)."""
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM posts 
                WHERE status = ? AND scheduled_for IS NOT NULL AND scheduled_for <= ?
                ORDER BY scheduled_for ASC
                """,
                (PostStatus.READY.value, now),
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def retry_failed(self, post_id: str) -> bool:
        """Reset failed post back to ready status for retry."""
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                UPDATE posts 
                SET status = ?, last_error = NULL, updated_at = ?
                WHERE id = ? AND status = ?
                """,
                (PostStatus.READY.value, now, post_id, PostStatus.FAILED.value),
            )
            conn.commit()
            return cursor.rowcount > 0
