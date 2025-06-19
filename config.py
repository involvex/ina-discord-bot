import os
import logging
import sys
import time

# --- Bot Version ---
__version__ = "0.2.109" # Centralized version

# --- Core Bot Config ---
OWNER_ID = 157968227106947072  # Your Discord User ID

# --- File Paths ---
BUILDS_FILE = 'saved_builds.json'
BOT_MANAGERS_FILE = 'bot_managers.json'
VERSION_FILE_PATH = 'VERSION' # For local VERSION file, if needed for consistency
DB_NAME = "new_world_data.db"
MASTER_SETTINGS_FILE = 'bot_settings.json'
TRACKED_RECIPES_FILE = 'tracked_recipes.json'

# --- Update Checker Configuration ---
GITHUB_REPO_OWNER = "involvex"
GITHUB_REPO_NAME = "ina-discord-bot" # Removed trailing hyphen
GITHUB_VERSION_FILE_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/main/VERSION"
UPDATE_CHECK_INTERVAL_SECONDS = 6 * 60 * 60  # Every 6 hours

# --- Logging ---
DEFAULT_LOG_LEVEL = logging.INFO
DEBUG_MODE_ENABLED = False # Tracks if debug mode is active

# --- Presence Rotation ---
NW_FUNNY_STATUSES = [
    {"name": "Terror Turkey", "state": "Being hunted... or hunting?"},
    {"name": "Truthahn des Schreckens", "state": "Wird gejagt... oder jagt?"},
    {"name": "Hanf für... Seile", "state": "Medizinische Zwecke, schwöre!"},
    {"name": "Angeln in Aeternum", "state": "Ob Fische als Währung gelten?"},
    {"name": "die Wildnis", "state": "Verlaufen. Sendet Kekse!"},
    {"name": "mit optionalen Bossen", "state": "Die waren nicht optional."},
    {"name": "Steuerverhandlungen", "state": "Mit dem Stadtverwalter."},
    {"name": "Inventar-Tetris", "state": "Und verliert schon wieder."},
    {"name": "Azoth-Management", "state": "Kritisch niedrig. Zu Fuß?"},
    {"name": "Holzfällerei", "state": "Die Bäume kennen meinen Namen."},
    {"name": "Friedensmodus", "state": "Tut nur so entspannt."},
    {"name": "Crafting-Wahnsinn", "state": "Kunst oder Schrott?"},
    {"name": "Expeditionen", "state": "Heiler hat Aggro. Klassiker."},
    {"name": "PvP", "state": "Sucht Streit, findet den Boden."},
    {"name": "Open World PvP", "state": "Von 5er-Gruppe 'gefairplayt.'"},
    {"name": "Belagerungskriege", "state": "Popcorn für die Lag-Show."},
    {"name": "Ganking 101", "state": "Plant episch, wird gegankt."},
    {"name": "PvP mit 1 HP", "state": "'Strategie', nicht Glück."},
    {"name": "Outpost Rush", "state": "Baroness Nash > Spieler."},
    {"name": "Skelette kloppen", "state": "Die haben 'nen Knochenjob."},
    {"name": "Dungeon Runs", "state": "Wer hat schon wieder gepullt?!"},
    {"name": "Elite-Gebiete", "state": "Alles will mich fressen."},
    {"name": "Questen", "state": "'Töte 10 Wildschweine'. Gähn."},
    {"name": "Korruptionsportale", "state": "Tentakel-Party!"},
    {"name": "Hardcore Aeternum", "state": "Died to a level 5 wolf."},
    {"name": "Hardcore Hiking", "state": "3h to Everfall. On foot."},
    {"name": "Hardcore Loot Drop", "state": "Everything gone. Thanks, Prowler."},
    {"name": "Hardcore with 1 Life", "state": "Trips. Game Over."},
    {"name": "Bot-Spotting", "state": "Player or lumberjack bot?"},
    {"name": "Resource Routes", "state": "Efficient. Or a bot."},
    {"name": "Combat Bots", "state": "Only light attacks. Always."},
    {"name": "GPS-guided Players", "state": "No deviation from the path."},
    {"name": "Silent Teammates", "state": "Focused or bot?"}
    # Add other statuses as needed
]
BOT_INVITE_URL = "https://discord.com/oauth2/authorize?client_id=1368579444209352754&scope=bot+applications.commands&permissions=8"
BOT_START_TIME = time.time() # Record bot start time

# --- Welcome Messages ---
NEW_WORLD_WELCOME_MESSAGES = [
    "Welcome to {guild_name}, {member_mention}! Grab your Azoth staff, a new adventure begins!",
    "A new challenger has arrived in {guild_name}! Welcome, {member_mention}! May your loot be epic.",
    "By the Spark, {member_mention} has joined us in {guild_name}! Watch out for those turkeys.",
    "{member_mention} just fast-traveled into {guild_name}! Hope you brought enough repair parts.",
    "The Corrupted didn't get this one! Welcome to {guild_name}, {member_mention}!",
    "Fresh off the boat and into {guild_name}! Welcome, {member_mention}. Try not to aggro everything.",
    "Look out, Aeternum, {member_mention} has arrived in {guild_name}! Let the grind commence.",
    "Is that a new Syndicate spy, {member_mention}? Or just a friendly adventurer joining {guild_name}? Welcome!",
    "Welcome, {member_mention}! May your bags be heavy and your Azoth always full here in {guild_name}.",
    "{member_mention} has breached the gates of {guild_name}! Prepare for glory (and maybe some lag).",
]

# --- Silly Messages ---
SILLY_MENTION_RESPONSES = [
    "Did someone say my name? Or was it just the wind in Aeternum?",
    "You summoned me! What grand adventure awaits? Or do you just need help with `/help`?",
    "I sense a disturbance in the Force... oh wait, wrong universe. How can I help you in Aeternum?",
    "Is that an Azoth staff in your pocket, or are you just happy to see me?",
    "I was just polishing my gear! What's up?",
    "Heard you were talking about me! Spill the corrupted beans!",
    "Yes? I'm here, probably not AFK like some adventurers I know.",
    "You rang? Hope it's not about another turkey invasion.",
    "I'm listening... unless there's a rare ore node nearby. Then I'm *really* listening.",
    "Speak, friend, and enter... my command list with `/help`!",
    "Beep boop! Just kidding, I'm powered by Aeternum's finest Azoth. What can I do for you?",
]

# --- Silly Uptime Messages for Presence ---
SILLY_UPTIME_MESSAGES = [
    "Chopping {x} Ironwood Trees for {uptime}",
    "Farming {x} Angry Earth Mobs for {uptime}",
    "Running {x} OPRs for {uptime}",
    "Crafting {x} Asmodeum for {uptime}",
    "Dodging {x} ganks on PvP Island for {uptime}",
    "Ignoring {x} town board quests for {uptime}",
    "Searching for {x} more Silk Threads for {uptime}",
    "Waiting {x} minutes in queue for {uptime}",
    "Polishing {x} trophies for {uptime}",
    "Telling {x} dad jokes in global for {uptime}",
    "Defending {x} forts for {uptime}"
]

def setup_logging():
    logging.basicConfig(
        level=DEFAULT_LOG_LEVEL,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    interactions_logger = logging.getLogger("interactions")
    interactions_logger.setLevel(DEFAULT_LOG_LEVEL)

# --- Data File URLs/Paths ---
ITEMS_CSV_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/main/items.csv" # Use GITHUB_REPO_NAME
PERKS_FILE = 'perks.csv' # Default filename for local perks CSV