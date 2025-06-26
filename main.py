# main.py
import os
import sys
from pathlib import Path
# --- Forcefully add project root to the Python path ---
# This is a robust way to ensure modules are found, even if the script is
# run from a different directory or with a misconfigured environment.
try:
    project_root = os.path.dirname(os.path.abspath(__file__))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
except Exception as e:
    # Use print as a fallback if logging fails
    print(f"CRITICAL: Could not set up sys.path. Error: {e}")
# --- End of new block ---

import asyncio
import time
import random # Added import for random
import subprocess # Added for git commands
import logging

from interactions import Activity, ActivityType

from config import (
    __version__ as config_version,
    NW_FUNNY_STATUSES,
    REPO_URL,
    BOT_START_TIME,
    SILLY_UPTIME_MESSAGES,
    DEV_MODE_UPDATE_INTERVAL,
    NORMAL_MODE_UPDATE_INTERVAL,
)
from bot_client import bot
from common_utils import format_uptime

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__) # Initialize logger at the top of the module
from settings_manager import get_dev_mode_setting
# Initialize logging
from config import setup_logging # Ensure setup_logging is imported from config
# We call setup_logging() here to ensure subsequent log messages are captured.
setup_logging() # Call setup_logging from config
logging.info(f"Project root '{project_root}' added to sys.path.")
logging.info(f"Current sys.path: {sys.path}")

# --- Background Tasks ---
async def rotate_funny_presence(bot_instance, interval=300): # Interval of 5 minutes
    """Periodically rotates the bot's presence with funny New World statuses and uptime."""
    await bot_instance.wait_until_ready()
    all_status_templates = NW_FUNNY_STATUSES + SILLY_UPTIME_MESSAGES
    while True:
        try:
            status_template = random.choice(all_status_templates)
            activity_name = status_template

            # Safely format the string, as some templates may not use all keys
            if "{uptime}" in status_template:
                uptime_seconds = time.time() - BOT_START_TIME
                formatted_uptime_str = format_uptime(uptime_seconds)
                activity_name = activity_name.replace("{uptime}", formatted_uptime_str)

            if "{x}" in status_template:
                random_x = random.randint(5, 500)
                activity_name = activity_name.replace("{x}", str(random_x))

            await bot_instance.change_presence(
                activity=Activity(name=activity_name, type=ActivityType.PLAYING)
            )
        except asyncio.CancelledError:
            logging.info("rotate_funny_presence task cancelled during shutdown.")
            break # Exit the loop gracefully
        except Exception as e:
            logging.warning(f"Failed to set presence: {e}")

        await asyncio.sleep(interval)

async def auto_update_task(bot_instance):
    """
    Periodically checks for updates from the Git repository and attempts to apply them.
    If dev mode is enabled, it will pull changes, install dependencies, and try to hot-reload.
    """
    await bot_instance.wait_until_ready()
    repo_path = Path(__file__).parent # The repo root is the directory containing main.py
    last_commit_hash_file = repo_path / ".last_commit_hash"

    def get_current_commit_hash():
        try:
            result = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=repo_path, check=True)
            return result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.error(f"Failed to get current git commit hash: {e}")
            return None

    def save_current_commit_hash(commit_hash):
        try:
            with open(last_commit_hash_file, "w") as f:
                f.write(commit_hash)
        except IOError as e:
            logger.error(f"Failed to save last commit hash: {e}")

    # Initialize last_known_commit_hash
    last_known_commit_hash = get_current_commit_hash()
    if last_known_commit_hash:
        save_current_commit_hash(last_known_commit_hash)
    else:
        logger.warning("Could not determine initial commit hash. Auto-update might not detect first changes correctly.")

    while True:
        if not get_dev_mode_setting():
            current_interval = NORMAL_MODE_UPDATE_INTERVAL
            logger.debug(f"Dev mode is disabled. Next auto-update check in {current_interval} seconds.")
        else:
            current_interval = DEV_MODE_UPDATE_INTERVAL
            logger.debug(f"Dev mode is enabled. Next auto-update check in {current_interval} seconds.")

        # Add a small random jitter to the interval
        sleep_duration = current_interval + random.randint(0, 60)
        await asyncio.sleep(sleep_duration)

        # Re-check dev mode after sleep, in case it was toggled during the sleep period
        if not get_dev_mode_setting():
            logger.debug("Dev mode was disabled during sleep. Skipping current auto-update check.")
            continue
        
        logger.info("Checking for bot updates...")
        try:
            # Fetch latest changes from remote
            subprocess.run(["git", "fetch", "origin"], cwd=repo_path, check=True)
            
            # Get the new commit hash from origin/main (or origin/master)
            result = subprocess.run(["git", "rev-parse", "origin/main"], capture_output=True, text=True, cwd=repo_path, check=True)
            new_commit_hash = result.stdout.strip()

            if new_commit_hash != last_known_commit_hash:
                logger.info(f"New update found! Current: {last_known_commit_hash[:7]}, New: {new_commit_hash[:7]}")
                
                # Pull changes
                subprocess.run(["git", "pull", "--ff-only"], cwd=repo_path, check=True)
                logger.info("Git pull successful.")

                # Install new dependencies
                subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], cwd=repo_path, check=True)
                logger.info("Dependencies updated.")

                # Attempt to hot-reload extensions
                logger.info("Attempting to hot-reload extensions...")
                # Use get_extensions() as .extensions attribute is deprecated/removed in newer interactions.py versions
                # This is a best-effort. Some changes (e.g., to main.py, config.py, or core libs) require a full restart.
                # for ext in list(bot_instance.get_extensions().keys()): # Iterate over a copy of keys
                # for ext in list(bot_instance.extensions.keys()):
                for ext in discover_extensions("commands", "events"):
                    try:
                        bot_instance.unload_extension(ext)
                        bot_instance.load_extension(ext)
                        logger.info(f"Reloaded extension: {ext}")
                    except Exception as e:
                        logger.error(f"Failed to hot-reload extension {ext}: {e}", exc_info=True)
                        logger.warning("A full bot restart might be required for all changes to take effect.")
                
                # Re-synchronize commands after reloading
                await bot_instance.synchronise_interactions()
                logger.info("Application commands re-synchronised after update.")

                last_known_commit_hash = new_commit_hash
                save_current_commit_hash(last_known_commit_hash)
                logger.info("Bot updated successfully (hot-reload attempted).")
            else:
                logger.debug("No new updates found.")

        except subprocess.CalledProcessError as e:
            logger.error(f"Git or pip command failed during auto-update: {e.stderr}", exc_info=True)
        except FileNotFoundError:
            logger.error("Git or pip command not found. Ensure Git is installed and in PATH, and Python is correctly set up.", exc_info=True)
        except Exception as e:
            logger.error(f"An unexpected error occurred during auto-update: {e}", exc_info=True)

def discover_extensions(*root_dirs: str) -> list[str]:
    """
    Dynamically discovers extensions in the specified root directories.
    Converts file paths like 'commands/new_world/items.py' to 'commands.new_world.items'.
    """
    extensions = []
    for root_dir in root_dirs:
        for path in Path(root_dir).rglob("*.py"):
            # Don't treat __init__.py or utils.py files as extensions, or files starting with '_' (private modules)
            if path.stem in ("__init__", "utils") or path.name.startswith("_"):
                continue
            extensions.append(".".join(path.with_suffix("").parts))
    return extensions

# --- Bot Events ---
@bot.event()
async def on_ready():
    """
    Called when the bot is ready. This can be called multiple times on reconnects.
    The initial setup (loading extensions, syncing commands) should only run once.
    """
    # This check prevents the setup from running again on reconnects
    if getattr(bot, "has_been_started", False):
        return

    logging.info("--------------------------------------------------")
    logging.info("Bot is performing first-time startup...")
    # To prevent rate limits from syncing on every extension load, we disable it temporarily
    bot.sync_ext = False

    # Load all command and event extensions
    extensions = discover_extensions("commands", "events")

    for extension in extensions:
        try:
            bot.load_extension(extension)
            logging.info(f"Successfully loaded extension: {extension}")
        except Exception as e:
            logging.error(f"Failed to load extension {extension}: {e}", exc_info=True)

    # Manually sync all commands once.
    try:
        await bot.synchronise_interactions()
        logging.info("Application commands successfully synchronised.")
    except Exception as e:
        logging.error(f"Failed to synchronise application commands: {e}", exc_info=True)
    bot.sync_ext = True

    # Set a flag to indicate that the initial setup is complete
    bot.has_been_started = True

    # Start background tasks
    # rotate_funny_presence is a general bot task and can remain here or be moved to a general extension.
    asyncio.create_task(rotate_funny_presence(bot, interval=300))
    
    asyncio.create_task(auto_update_task(bot)) # Start the auto-update task
    logging.info(f"Ina is ready! Logged in as {bot.user.username} ({bot.user.id})")
    logging.info(f"Version: {config_version}")
    logging.info("--------------------------------------------------")

# --- Main Execution ---
import sqlite3
import sys
from config import DB_NAME

def is_db_valid(db_path: str) -> bool:
    """
    Checks if a file is a valid, non-empty SQLite database.
    """
    if not os.path.exists(db_path) or os.path.getsize(db_path) == 0:
        return False
    try:
        conn = sqlite3.connect(db_path)
        # A quick query to the master table is a fast and effective validity check.
        conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        conn.close()
        return True
    except sqlite3.DatabaseError:
        return False

def load_all_game_data():
    """
    Ensures the SQLite database exists and is valid before the bot starts.
    If the DB is missing or corrupted, it triggers a recreation.
    """
    logging.info("Verifying game data source (SQLite Database)...")

    # If the DB exists but is invalid, remove it to force recreation.
    if os.path.exists(DB_NAME) and not is_db_valid(DB_NAME):
        logging.warning(f"Database '{DB_NAME}' found but is invalid/corrupted. Removing to force recreation.")
        try:
            os.remove(DB_NAME)
        except Exception as e:
            logging.critical(f"Could not remove corrupted DB file: {e}. Please fix permissions and restart.", exc_info=True)
            sys.exit(1)

    # If the DB doesn't exist (either initially or after being removed), create it.
    if not os.path.exists(DB_NAME):
        logging.info(f"Database '{DB_NAME}' not found. Attempting to create and populate it now...")
        try:
            from create_db import populate_db
            populate_db()
        except Exception as e:
            logging.critical(f"Failed to create and populate database: {e}", exc_info=True)
            sys.exit(1)

    # Final check to ensure we have a valid DB before proceeding.
    if not is_db_valid(DB_NAME):
        logging.critical(f"Database '{DB_NAME}' is still invalid after creation attempt. Exiting.")
        sys.exit(1)

    logging.info(f"Database '{DB_NAME}' is available and valid. Bot will use it for data lookups.")

    logging.info("Game data verification/creation process complete.")

if __name__ == "__main__":
    # Ensure the database exists before starting the bot
    # This is a synchronous call before the async loop starts
    load_all_game_data()

    # The bot token is handled in bot_client.py, so we just start the bot here.
    # Set sync_interactions=False to prevent automatic command syncing on every startup
    # This relies on the /manage update command to sync commands.
    bot.start()
