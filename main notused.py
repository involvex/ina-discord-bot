# main.py
import os
import sys
import asyncio
import time
import random # Added import for random
import logging

from interactions import Activity, ActivityType

# --- Configuration & Setup ---
from config import (
    __version__ as config_version,
    NW_FUNNY_STATUSES,
    BOT_START_TIME,
    SILLY_UPTIME_MESSAGES,
)
from bot_client import bot
# Add the project root directory to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from common_utils import format_uptime

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Initialize logging
from config import setup_logging # Ensure setup_logging is imported from config
setup_logging() # Call setup_logging from config

# --- Background Tasks ---
async def rotate_funny_presence(bot_instance, interval=300): # Interval of 5 minutes
    """Periodically rotates the bot's presence with funny New World statuses and uptime."""
    await bot_instance.wait_until_ready()
    
    while True:
        try:
            # Decide whether to show a funny status or an uptime message
            if random.random() < 0.7: # 70% chance for funny status
                status_entry = random.choice(NW_FUNNY_STATUSES)
                activity_name = f"{status_entry['name']} – {status_entry['state']}"
            else: # 30% chance for uptime message
                uptime_seconds = time.time() - BOT_START_TIME
                formatted_uptime_str = format_uptime(uptime_seconds)
                silly_template = random.choice(SILLY_UPTIME_MESSAGES)
                random_x = random.randint(5, 500) # Adjust range as needed
                activity_name = silly_template.format(x=random_x, uptime=formatted_uptime_str)

            await bot_instance.change_presence(
                activity=Activity(name=activity_name, type=ActivityType.PLAYING)
            )
        except Exception as e:
            logging.warning(f"Failed to set presence: {e}")

        await asyncio.sleep(interval)

# --- Bot Events ---
@bot.event()
async def on_ready():
    """
    Called when the bot is ready and connected to Discord.
    Loads all command and event extensions and starts background tasks.
    """
    print("--------------------------------------------------")
    logging.info("Bot is starting up...")

    # Load all command and event extensions
    # Note: commands.admin will schedule its own check_for_updates task
    extensions = [
        "commands.general", 
        "commands.new_world.items", # Loads /nwdb and /perk
        "commands.new_world.crafting", # Loads /recipe and /calculate_craft
        "commands.admin", 
        "commands.settings_commands", "events.guild_events", "events.message_events"
    ]
    for extension in extensions:
        try:
            bot.load_extension(extension)
            logging.info(f"Successfully loaded extension: {extension}")
        except Exception as e:
            logging.error(f"Failed to load extension {extension}: {e}", exc_info=True)

    # Start background tasks
    # rotate_funny_presence is a general bot task and can remain here or be moved to a general extension.
    asyncio.create_task(rotate_funny_presence(bot, interval=300))
    
    logging.info(f"Ina is ready! Logged in as {bot.user.username} ({bot.user.id})")
    logging.info(f"Version: {config_version}")
    print("--------------------------------------------------")

# --- Main Execution ---
import sqlite3
from config import DB_NAME

def load_all_game_data():
    """
    Ensures the SQLite database file exists. If not, attempts to create and populate it.
    The actual data loading into the DB is handled by create_db.py.
    """
    logging.info("Verifying game data source (SQLite Database)...")

    if not os.path.exists(DB_NAME):
        logging.warning(
            f"Database file '{DB_NAME}' not found. Attempting to create and populate it now. "
            f"This may take some time and consume resources..."
        )
        try:
            from create_db import populate_db # Import here to avoid potential circular import issues at module load time
            populate_db() # This function from create_db.py prints its own progress
            if os.path.exists(DB_NAME):
                logging.info(f"Database '{DB_NAME}' created and populated successfully.")
            else:
                # This case means populate_db ran but didn't create the file, which indicates an issue in populate_db
                logging.error(
                    f"CRITICAL: populate_db() completed but database file '{DB_NAME}' still not found. "
                    f"Bot may not function correctly for data-dependent commands."
                )
        except ImportError:
            logging.error(
                "CRITICAL: Could not import 'populate_db' from 'create_db.py'. "
                "Database cannot be automatically created. Please run 'create_db.py' manually if possible."
            )
        except Exception as e:
            logging.error(
                f"CRITICAL: An error occurred while trying to automatically create/populate the database '{DB_NAME}': {e}. "
                f"Please run 'create_db.py' manually if possible. Bot may not function correctly.", exc_info=True
            )
    
    if os.path.exists(DB_NAME):
        logging.info(f"Database '{DB_NAME}' is available. Bot will use it for data lookups.")
    else:
        logging.critical(
            f"CRITICAL: Database file '{DB_NAME}' not found. "
            f"The bot relies on this database for item, perk, and recipe data. "
            f"Automatic creation failed or was not possible. Please ensure 'create_db.py' can run successfully or create the DB manually."
        )
    logging.info("Game data verification/creation process complete.")

if __name__ == "__main__":
    # Ensure the database exists before starting the bot
    # This is a synchronous call before the async loop starts
    load_all_game_data()

    # The bot token is handled in bot_client.py, so we just start the bot here.
    # Set sync_interactions=False to prevent automatic command syncing on every startup
    # This relies on the /manage update command to sync commands.
    bot.start()
