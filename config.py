import os
import logging
import sys

# --- Bot Version ---
__version__ = "0.2.4"

# --- Core Bot Config ---
OWNER_ID = 157968227106947072  # Your Discord User ID

# --- File Paths ---
BUILDS_FILE = 'saved_builds.json'
BOT_MANAGERS_FILE = 'bot_managers.json'
VERSION_FILE_PATH = 'VERSION' # For local VERSION file, if needed for consistency

# --- Update Checker Configuration ---
GITHUB_REPO_OWNER = "involvex"
GITHUB_REPO_NAME = "ina-discord-bot-"
GITHUB_VERSION_FILE_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/main/VERSION"
UPDATE_CHECK_INTERVAL_SECONDS = 6 * 60 * 60  # Every 6 hours

# --- Presence Rotation ---
NW_FUNNY_STATUSES = [
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
    # Add other statuses as needed
]
BOT_INVITE_URL = "https://discord.com/oauth2/authorize?client_id=1368579444209352754&scope=bot+applications.commands&permissions=8"

def setup_logging():
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logging.getLogger("interactions").setLevel(logging.DEBUG) # Or logging.INFO for less verbosity