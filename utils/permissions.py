import json
import logging
from config import BOT_MANAGERS_FILE, OWNER_ID

def load_bot_managers() -> list[int]:
    """Loads the list of bot manager user IDs from the JSON file."""
    try:
        with open(BOT_MANAGERS_FILE, 'r', encoding='utf-8') as f:
            manager_ids = json.load(f)
            if isinstance(manager_ids, list) and all(isinstance(uid, int) for uid in manager_ids):
                return manager_ids
            logging.warning(f"Corrupted data in {BOT_MANAGERS_FILE}. Expected list of ints.")
            return []
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        logging.error(f"Error decoding JSON from {BOT_MANAGERS_FILE}. Returning empty list.")
        return []

def save_bot_managers(manager_ids: list[int]):
    """Saves the list of bot manager user IDs to the JSON file."""
    try:
        with open(BOT_MANAGERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(manager_ids, f, indent=2)
    except IOError as e:
        logging.error(f"Error writing to {BOT_MANAGERS_FILE}: {e}")

def is_bot_manager(user_id: int) -> bool:
    """Checks if a user is a designated bot manager or the bot owner."""
    return user_id == OWNER_ID or user_id in load_bot_managers()