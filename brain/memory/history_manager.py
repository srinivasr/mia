import sqlite3
import json
import threading
from pathlib import Path
import sys
from datetime import datetime
from utils.logger import setup_logger

logger = setup_logger("HistoryManager")

def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

DB_PATH = get_base_dir() / "memory" / "history.db"

# Thread-local storage for SQLite connections since they can't be shared across threads
_local = threading.local()

def get_db():
    if not hasattr(_local, "conn"):
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        # Using check_same_thread=False since we use a local dict, but it's safe anyway.
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        _init_db(conn)
        _local.conn = conn
    return _local.conn

def _init_db(conn):
    try:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                role TEXT,
                content TEXT,
                type TEXT
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON messages (timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_session ON messages (session_id)')
        conn.commit()
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")

def log_message(session_id: str, role: str, content: str, msg_type: str = "text"):
    """
    Logs a single message into the history.
    role: "user", "assistant", or "system" (for tools)
    type: "text", "tool_call", "tool_result"
    """
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO messages (session_id, role, content, type) VALUES (?, ?, ?, ?)',
            (session_id, role, content, msg_type)
        )
        conn.commit()
        logger.debug(f"Logged {role} message ({msg_type})")
    except Exception as e:
        logger.error(f"Failed to log message: {e}")

def get_recent_context(limit: int = 100) -> str:
    """
    Retrieves the most recent messages and formats them into a single context string.
    """
    try:
        conn = get_db()
        cursor = conn.cursor()
        # Fetch the last `limit` rows, ordered chronologically ascending
        cursor.execute('''
            SELECT role, content, type, timestamp 
            FROM (
                SELECT role, content, type, timestamp
                FROM messages
                ORDER BY timestamp DESC
                LIMIT ?
            )
            ORDER BY timestamp ASC
        ''', (limit,))
        
        rows = cursor.fetchall()
        if not rows:
            return ""

        context_lines = []
        for row in rows:
            role = row['role'].upper()
            content = row['content']
            msg_type = row['type']
            
            # Simple formatting depending on type
            if msg_type == 'tool':
                context_lines.append(f"[{role} - TOOL EXECUTION]: {content}")
            else:
                context_lines.append(f"{role}: {content}")
                
        context_str = "\n".join(context_lines)
        return f"[RECENT CONVERSATION HISTORY]\n{context_str}\n"

    except Exception as e:
        logger.error(f"Failed to get recent context: {e}")
        return ""

def clear_history():
    """Clear all conversation history. Usually for debugging or hard resets."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM messages')
        conn.commit()
        logger.info("Conversation history cleared.")
    except Exception as e:
        logger.error(f"Failed to clear history: {e}")
