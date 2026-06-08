import sqlite3
import threading
from memory.history_manager import get_db
from utils.logger import setup_logger

logger = setup_logger("Summarizer")

# A placeholder for future implementation of rolling summaries.
# It can run asynchronously in the background.

def trigger_background_summarization(session_id: str):
    """
    Triggers a background thread to summarize old messages if they exceed a certain limit.
    This prevents the context window from blowing up over extremely long sessions.
    """
    def _summarize():
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM messages WHERE session_id = ?', (session_id,))
            count = cursor.fetchone()[0]
            
            if count > 50:
                logger.info(f"Session {session_id} has {count} messages. Ready for summarization (not yet fully implemented).")
                # TODO: Implement rolling summary via lightweight Gemini model
                # to compress messages N-50 to N-20 into long-term history.
                pass
        except Exception as e:
            logger.error(f"Summarization error: {e}")

    thread = threading.Thread(target=_summarize, daemon=True)
    thread.start()
