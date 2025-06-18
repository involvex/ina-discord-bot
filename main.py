import os
import sys
import random
import logging
import asyncio
import uuid
import math
import subprocess
import platform # For OS detection
import unicodedata
import re
import items
import perks
from interactions import Client, slash_command, slash_option, OptionType, Permissions, Embed, Activity, ActivityType, User, SlashContext, File, Member, ChannelType, Message, Role
from interactions.models.discord.channel import GuildText # For specific channel type checking
from typing import Optional
import packaging.version  # For version comparison
from recipes import get_recipe, calculate_crafting_materials, RECIPES
from utils.image_utils import generate_petpet_gif
import json
from bs4 import BeautifulSoup
import requests

# Load environment variables from .env file
from dotenv import load_dotenv
import datetime # For timestamps in logs

load_dotenv()

__version__ = "0.2.42" 

logging.basicConfig(
    level=logging.DEBUG, # Temporarily change to DEBUG to see more detailed update check logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logging.getLogger("interactions").setLevel(logging.DEBUG)

bot_token = os.getenv("BOT_TOKEN")
if not bot_token:
    print("Error: BOT_TOKEN not found in .env file. Please make sure it is set.")
    sys.exit(1)

bot = Client(token=bot_token)

BUILDS_FILE = 'saved_builds.json' # Kept separate for user-generated content
MASTER_SETTINGS_FILE = 'bot_settings.json'
OWNER_ID = 157968227106947072 # Your Discord User ID

# --- Update Checker Configuration ---
GITHUB_REPO_OWNER = "involvex"
GITHUB_REPO_NAME = "ina-discord-bot-" # Added trailing hyphen
# URL to a file on the main branch containing the version string (e.g., "0.1.1")
GITHUB_VERSION_FILE_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/main/VERSION"
UPDATE_CHECK_INTERVAL_SECONDS = 6 * 60 * 60  # Periodic check interval (e.g., every 6 hours)

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

# --- Global Data Stores ---
ITEM_DATA = {}
ALL_PERKS_DATA = {}
ITEM_ID_TO_NAME_MAP = {} # For mapping Item IDs to Names

# --- Master Settings Helper Functions ---
def load_master_settings():
    """Loads all settings from the master JSON file. Creates it with defaults if not found."""
    try:
        with open(MASTER_SETTINGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Return a default structure if file doesn't exist or is invalid
        default_settings = {
            "bot_managers": [],
            "guild_settings": {} # Guild-specific settings will be nested here
        }
        save_master_settings(default_settings) # Create the file with defaults
        return default_settings

def save_master_settings(settings_data):
    """Saves the provided settings data to the master JSON file."""
    with open(MASTER_SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings_data, f, indent=4)


# --- Bot Manager Helper Functions ---
def load_bot_managers():
    """Loads bot manager IDs from the master settings file."""
    settings = load_master_settings()
    return settings.get("bot_managers", [])

def save_bot_managers(managers_list):
    """Saves the bot managers list to the master settings file."""
    settings = load_master_settings()
    settings["bot_managers"] = managers_list
    save_master_settings(settings)

# --- Welcome Message Helper Functions (using master settings) ---
def save_welcome_setting(guild_id: str, enabled: bool, channel_id: Optional[str]):
    """Saves welcome message settings for a specific guild in the master settings file."""
    settings = load_master_settings()
    guild_id_str = str(guild_id)

    guild_specific_settings = settings.setdefault("guild_settings", {})
    this_guild_settings = guild_specific_settings.setdefault(guild_id_str, {})
    
    this_guild_settings["welcome"] = {
        "enabled": enabled,
        "channel_id": str(channel_id) if channel_id else None
    }
    save_master_settings(settings)

def get_welcome_setting(guild_id: str) -> Optional[dict]:
    """Gets welcome message settings for a specific guild from the master settings file."""
    settings = load_master_settings()
    return settings.get("guild_settings", {}).get(str(guild_id), {}).get("welcome")

# --- Logging Helper Functions (using master settings) ---
def save_logging_setting(guild_id: str, enabled: bool, channel_id: Optional[str]):
    """Saves server activity logging settings for a specific guild in the master settings file."""
    settings = load_master_settings()
    guild_id_str = str(guild_id)

    guild_specific_settings = settings.setdefault("guild_settings", {})
    this_guild_settings = guild_specific_settings.setdefault(guild_id_str, {})

    this_guild_settings["logging"] = {
        "enabled": enabled,
        "channel_id": str(channel_id) if channel_id else None
    }
    save_master_settings(settings)

def get_logging_setting(guild_id: str) -> Optional[dict]:
    """Gets server activity logging settings for a specific guild from the master settings file."""
    settings = load_master_settings()
    return settings.get("guild_settings", {}).get(str(guild_id), {}).get("logging")


def is_bot_manager(user_id: int) -> bool:
    """Checks if a user is the owner or a permitted bot manager."""
    if user_id == OWNER_ID:
        return True
    managers = load_bot_managers()
    return user_id in managers

def add_bot_manager(user_id: int) -> bool:
    """Adds a user to the bot managers list. Returns True if added, False if already present."""
    managers = load_bot_managers()
    if user_id not in managers:
        managers.append(user_id)
        save_bot_managers(managers)
        return True
    return False

def remove_bot_manager(user_id: int) -> bool:
    """Removes a user from the bot managers list. Returns True if removed, False if not found."""
    managers = load_bot_managers()
    if user_id in managers:
        managers.remove(user_id)
        save_bot_managers(managers)
        return True
    return False

@slash_command("ping", description="Check if the bot is online.")
async def ping(ctx):
    latency_ms = round(bot.latency * 1000)
    await ctx.send(f"Pong! Ina is online. Latency: {latency_ms}ms")


@slash_command("help", description="Show all available commands and their descriptions")
@slash_option("command", "Get detailed help for a specific command", opt_type=OptionType.STRING, required=False)
async def help_command(ctx, command: Optional[str] = None):
    commands = {
        "ping": "Check if the bot is online.",
        "help": "Show all available commands and their descriptions.",
        "petpet": "Give a New World petting ritual to a user!",
        "calculate": "Perform a calculation with New World magic!",
        "nwdb": "Look up items from New World Database.",
        "calculate_craft": "Calculate all resources needed to craft an item, including intermediates.",
        "recipe": "Show the full recipe breakdown for a craftable item and track it.",
        "addbuild": "Add a build from nw-buddy.de with a name and optional key perks.",
        "build list": "Show a list of saved builds.",
        "build add": "Add a build from nw-buddy.de with a name and optional key perks.",
        "build remove": "Remove a saved build (requires 'Manage Server' permission).",
        "removebuild": "Remove a saved build (requires 'Manage Server' permission).",
        "perk": "Look up information about a specific New World perk.",
        "about": "Show information about Ina's New World Bot.",
        "manage update": f"Triggers the bot's update script (Owner only: <@{OWNER_ID}>).",
        "manage restart": "Requests the bot to shut down for a manual restart (Bot Owner/Manager only).",
        "settings permit": "Grants a user bot management permissions (Server Administrator or Bot Owner only).",
        "settings unpermit": "Revokes a user's bot management permissions (Server Administrator or Bot Owner only).", # Keep
        "settings listmanagers": "Lists users with bot management permissions (Server Administrator or Bot Owner only).", 
        "settings welcomemessages": "Manage welcome messages. Actions: enable, disable, status. [channel] option required for 'enable'.",
        "settings logging": "Manage server activity logging. Actions: enable, disable, status. [channel] option required for 'enable'."
    }
    if command and command.lower() in commands:
        await ctx.send(f"**/{command.lower().split()[0]}**: {commands[command.lower()]}") # Use split for commands with options in help
    else:
        header = "**Ina's New World Bot Commands:**\n"
        full_help_text = header
        current_page_lines = []

        for cmd, desc in commands.items():
            line = f"**/{cmd}**: {desc}"
            # Check if adding the next line would exceed the limit (approximate)
            # 2000 - current_page_length - new_line_length - buffer for markdown/etc.
            if len(full_help_text) + len("\n".join(current_page_lines)) + len(line) + 50 > 1950: # 1950 to be safe
                await ctx.send(full_help_text + "\n".join(current_page_lines))
                current_page_lines = [line] # Start new page
                full_help_text = "" # Reset header for subsequent pages if needed, or add (continued)
            else:
                current_page_lines.append(line)
        
        # Send any remaining lines
        if current_page_lines:
            await ctx.send(full_help_text + "\n".join(current_page_lines))



@slash_command("petpet", description="Give a New World petting ritual to a user!")
@slash_option("user", "The user to pet (Aeternum style)", opt_type=OptionType.USER, required=True)
async def petpet(ctx, user):
    await ctx.defer() # Defer response as GIF generation can take a moment

    avatar_url = user.avatar_url
    if not avatar_url:
        # Fallback if avatar_url is None (e.g., for users with default avatars)
        # user.display_avatar should provide a URL even for default avatars.
        avatar_url = user.display_avatar.url

    if not avatar_url: # Still no URL, something is wrong
        await ctx.send("Could not retrieve avatar for the user.", ephemeral=True)
        return

    gif_buffer = await generate_petpet_gif(str(avatar_url)) # Ensure URL is a string

    if gif_buffer:
        await ctx.send(files=[File(file=gif_buffer, file_name="petpet.gif")])
    else:
        await ctx.send("Sorry, I couldn't create the petpet animation right now. Maybe the winds of Aeternum are too wild!", ephemeral=True)

@slash_command("calculate", description="Perform a calculation with New World magic!")
@slash_option("expression", "The mathematical expression to calculate", opt_type=OptionType.STRING, required=True)
async def calculate(ctx, expression: str):
    try:
        allowed_names = {k: v for k, v in math.__dict__.items() if not k.startswith("_")}
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        await ctx.send(f"🔮 The result of `{expression}` is `{result}`.")
    except Exception as e:
        await ctx.send(f"The arcane calculation failed: {e}", ephemeral=True)


@slash_command(name="nwdb", description="Look up items from New World Database.")
@slash_option("item_name", "The name of the item to look up", opt_type=OptionType.STRING, required=True, autocomplete=True)
async def nwdb(ctx, item_name: str):
    await ctx.defer() # Defer the response immediately
    # Load items from CSV
    # item_data = items.load_items_from_csv('items.csv') # No longer load here
    if not ITEM_DATA:
        await ctx.send("Item data is not loaded. Please try again later or contact an admin.", ephemeral=True)
        return
    item_name_lower = item_name.lower()
    if item_name_lower not in ITEM_DATA:
        await ctx.send(f"Item '{item_name}' not found in the database.", ephemeral=True)
        return
    item = ITEM_DATA[item_name_lower]
    def get_any(item, keys, default):
        for k in keys:
            if k in item and item[k]:
                return item[k]
        return default
    name = get_any(item, ['name', 'Name', 'Item Name'], item_name)
    item_id_for_url = get_any(item, ['Item ID', 'item_id'], None)

    description = get_any(item, ['description', 'Description', 'Flavor Text'], 'No description available.')
    rarity = get_any(item, ['rarity', 'Rarity'], 'Unknown')
    tier = get_any(item, ['tier', 'Tier'], 'Unknown')
    icon_url = get_any(item, ['icon', 'Icon', 'Icon Path', 'icon_url'], None)
    
    # Build a NWDB-style embed
    embed = Embed()
    embed.title = name
    if item_id_for_url:
        embed.url = f"https://nwdb.info/db/item/{item_id_for_url}"
    else:
        logging.warning(f"Could not find Item ID for '{name}' to create NWDB link.")

    embed.color = 0x9b59b6 if rarity.lower() == 'artifact' else 0x7289da
    if icon_url:
        embed.set_thumbnail(url=icon_url)
    embed.add_field(name="Rarity", value=rarity, inline=True)
    embed.add_field(name="Tier", value=tier, inline=True)
    if description and not description.startswith('Artifact_'):
        embed.add_field(name="Description", value=description, inline=False)
    # Add more NWDB-style fields if available
    # Example: Gear Score, Perks, etc.
    gear_score = get_any(item, ['gear_score', 'Gear Score', 'GS'], None)
    if gear_score:
        embed.add_field(name="Gear Score", value=str(gear_score), inline=True)
    # Perks (if present)
    perks = get_any(item, ['perks', 'Perks'], None)
    # Perk pretty names and icons mapping (expand as needed)
    PERK_PRETTY = {
        'PerkID_Artifact_Set1_HeavyChest': ("Artifact Set: Heavy Chest", "🟣"),
        'PerkID_Gem_EmptyGemSlot': ("Empty Gem Slot", "💠"),
        'PerkID_Armor_DefBasic': ("Basic Defense", "🛡️"),
        'PerkID_Armor_RangeDefense_Physical': ("Ranged Physical Defense", "🏹"),
        # Add more known perks here...
    }
    if perks:
        perk_lines = []
        for perk in str(perks).split(","):
            perk = perk.strip()
            if not perk:
                continue
            pretty, icon = PERK_PRETTY.get(perk, (perk, '•'))
            perk_lines.append(f"{icon} {pretty}")
        if perk_lines:
            embed.add_field(name="Perks", value="\n".join(perk_lines), inline=False)
    # If item is craftable, mention calculate_craft
    if get_recipe(item_name, ITEM_DATA, ITEM_ID_TO_NAME_MAP):
        embed.set_footer(text=f"Type /calculate_craft item_name:{item_name} amount:4 to calculate resources!")
    await ctx.send(embeds=embed)


@nwdb.autocomplete("item_name")
async def nwdb_autocomplete(ctx):
    # Provide autocomplete suggestions from items.csv
    if not ITEM_DATA:
        await ctx.send(choices=[])
        return

    search_term = ctx.input_text.lower().strip() if ctx.input_text else ""

    if not search_term: # If search term is empty, send no choices or a placeholder
        await ctx.send(choices=[])
        # Or, send a placeholder:
        # await ctx.send(choices=[{"name": "Type an item name to search...", "value": "_placeholder_"}])
        return

    # Optimization: If search term is very short, it might still be too many matches.
    # For example, limit search if term is less than 2 or 3 characters.
    # For now, we'll proceed with the search but this is an area for further optimization if needed.

    matches_keys = []
    # ITEM_DATA.keys() are already lowercase
    for item_key_lower in ITEM_DATA.keys():
        if search_term in item_key_lower:
            matches_keys.append(item_key_lower)
            if len(matches_keys) >= 25: # Limit to 25 matches early
                break

    choices = []
    for match_key_lower in matches_keys: # Iterate only up to 25 found matches
        # Assuming item_data[match_key] is a dict containing item details
        # and has a field like 'Name' or 'name' for the display name.
        # Fallback to title-cased key if specific name field isn't found.
        item_details = ITEM_DATA.get(match_key_lower, {})
        # Use the 'name' field from the loaded item_data which should have original casing
        display_name = item_details.get('Name', item_details.get('name', match_key_lower.title()))
        choices.append({"name": display_name, "value": match_key_lower}) # Send the key (lowercase) as value

    # Discord allows max 25 choices
    await ctx.send(choices=choices)

@slash_command(name="calculate_craft", description="Calculate all resources needed to craft an item, including intermediates.")
@slash_option("item_name", "The name of the item to craft", opt_type=OptionType.STRING, required=True, autocomplete=True)
@slash_option("amount", "How many to craft", opt_type=OptionType.INTEGER, required=False)
async def calculate_craft(ctx, item_name: str, amount: int = 1):
    await ctx.defer() # Defer response
    recipe = get_recipe(item_name, ITEM_DATA, ITEM_ID_TO_NAME_MAP)
    if not recipe:
        await ctx.send(f"No recipe found for '{item_name}'.", ephemeral=True)
        return
    # Show all resources, including intermediates
    all_materials = calculate_crafting_materials(item_name, ITEM_DATA, ITEM_ID_TO_NAME_MAP, amount or 1, include_intermediate=True)
    if not all_materials:
        await ctx.send(f"Could not calculate materials for '{item_name}'.", ephemeral=True)
        return
    lines = [f"To craft {amount or 1} **{item_name.title()}** you need (including intermediates):"]
    for mat, qty in all_materials.items():
        lines.append(f"• {qty} {mat.title()}")
    await ctx.send("\n".join(lines))


@calculate_craft.autocomplete("item_name")
async def calculate_craft_autocomplete(ctx):
    search_term = ctx.input_text.lower().strip() if ctx.input_text else ""

    if not search_term:
        await ctx.send(choices=[])
        return

    matches = []
    # RECIPES keys are already lowercase if defined consistently
    for recipe_key_lower in RECIPES.keys():
        if search_term in recipe_key_lower:
            matches.append(recipe_key_lower)
            if len(matches) >= 25:
                break
    
    choices = [{"name": name.title(), "value": name} for name in matches]
    await ctx.send(choices=choices)


@slash_command(name="recipe", description="Show the full recipe breakdown for a craftable item and track it.")
@slash_option("item_name", "The name of the item to show the recipe for", opt_type=OptionType.STRING, required=True, autocomplete=True)
async def recipe(ctx, item_name: str):
    await ctx.defer() # Defer response

    from recipes import get_recipe, fetch_recipe_from_nwdb, track_recipe
    recipe = get_recipe(item_name, ITEM_DATA, ITEM_ID_TO_NAME_MAP)
    if not recipe:
        # Try to fetch from nwdb.info
        recipe = fetch_recipe_from_nwdb(item_name)
        if not recipe:
            await ctx.send(f"No recipe found for '{item_name}'.", ephemeral=True)
            return
        else:
            await ctx.send(f"Recipe for '{item_name}' fetched from nwdb.info.")
    # Track the recipe for the user
    user_id = str(ctx.author.id)
    track_recipe(user_id, item_name, recipe)
    embed = Embed()
    embed.title = f"Recipe: {item_name.title()}"
    embed.color = 0x9b59b6
    embed.add_field(name="Station", value=recipe.get("station", "-"), inline=True)
    embed.add_field(name="Skill", value=f"{recipe.get('skill', '-')}" , inline=True)
    embed.add_field(name="Skill Level", value=str(recipe.get("skill_level", "-")), inline=True)
    embed.add_field(name="Tier", value=str(recipe.get("tier", "-")), inline=True)
    # Ingredients breakdown
    ing_lines = []
    for ing in recipe.get("ingredients", []):
        ing_lines.append(f"• {ing['quantity']} {ing['item']}")
    
    # Add NWDB link for the crafted item
    item_details_for_recipe = ITEM_DATA.get(item_name.lower())
    if item_details_for_recipe:
        item_id_for_url = item_details_for_recipe.get('Item ID')
        if item_id_for_url:
            embed.add_field(name="NWDB Link", value=f"[View on NWDB](https://nwdb.info/db/item/{item_id_for_url})", inline=False)

    embed.add_field(name="Ingredients", value="\n".join(ing_lines) or "-", inline=False)
    await ctx.send(embeds=embed)


@recipe.autocomplete("item_name")
async def recipe_autocomplete(ctx):
    search_term = ctx.input_text.lower().strip() if ctx.input_text else ""

    if not ITEM_DATA:
        await ctx.send(choices=[])
        return
    
    if not search_term:
        await ctx.send(choices=[])
        return

    matches_keys = []
    for item_key_lower in ITEM_DATA.keys(): # ITEM_DATA keys are already lowercase
        # We also want to check if the item is in RECIPES, as /recipe is for craftable items
        if search_term in item_key_lower and (item_key_lower in RECIPES or get_recipe(item_key_lower, ITEM_DATA, ITEM_ID_TO_NAME_MAP)): # Check if a recipe exists
            matches_keys.append(item_key_lower)
            if len(matches_keys) >= 25:
                break

    choices = []
    for match_key_lower in matches_keys:
        item_details = ITEM_DATA.get(match_key_lower, {})
        display_name = item_details.get('Name', item_details.get('name', match_key_lower.title()))
        choices.append({"name": display_name, "value": match_key_lower})

    await ctx.send(choices=choices)

# --- Build Management Commands ---
@slash_command(name="build", description="Manage saved New World builds.")
async def build_group(ctx: SlashContext):
    """Base command for build management."""
    pass

@build_group.subcommand(sub_cmd_name="add", sub_cmd_description="Add a build from nw-buddy.de.")
@slash_option("link", "The nw-buddy.de build link", opt_type=OptionType.STRING, required=True)
@slash_option("name", "A name for this build", opt_type=OptionType.STRING, required=True)
@slash_option("keyperks", "Comma-separated list of key perks (optional, paste from Perk stacks)", opt_type=OptionType.STRING, required=False)
async def build_add(ctx: SlashContext, link: str, name: str, keyperks: str = None):
    import requests
    from bs4 import BeautifulSoup
    import re
    # Validate link
    if not re.match(r"^https://(www\.)?nw-buddy.de/gearsets/", link):
        await ctx.send("Please provide a valid nw-buddy.de gearset link.", ephemeral=True)
        return
    perks_list = []
    if keyperks:
        perks_list = [p.strip() for p in keyperks.split(',') if p.strip()]
    else:
        try:
            resp = requests.get(link, timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                # Look for 'Perk stacks' section
                perk_header = soup.find(lambda tag: tag.name in ['h2', 'h3', 'h4'] and 'perk stacks' in tag.get_text(strip=True).lower())
                if perk_header:
                    # Find the next ul or div after the header
                    next_elem = perk_header.find_next(['ul', 'div'])
                    if next_elem:
                        for li in next_elem.find_all(['li', 'div'], recursive=False):
                            text = li.get_text(strip=True)
                            if text:
                                perks_list.append(text)
        except Exception:
            pass
    # Save build
    try:
        with open(BUILDS_FILE, 'r', encoding='utf-8') as f:
            builds = json.load(f)
    except Exception:
        builds = [] # Initialize as an empty list if file not found or error
    builds.append({"name": name, "link": link, "keyperks": perks_list, "submitted_by": ctx.author.id})
    with open(BUILDS_FILE, 'w', encoding='utf-8') as f:
        json.dump(builds, f, indent=2)
    await ctx.send(f"Build '{name}' added!", ephemeral=True)


@build_group.subcommand(sub_cmd_name="list", sub_cmd_description="Show a list of saved builds.")
async def build_list(ctx: SlashContext):
    try:
        with open(BUILDS_FILE, 'r', encoding='utf-8') as f:
            builds = json.load(f)
    except Exception:
        await ctx.send("No builds saved yet.", ephemeral=True)
        return
    if not builds:
        await ctx.send("No builds saved yet.", ephemeral=True)
        return
    embed = Embed()
    embed.title = "Saved Builds"
    embed.color = 0x3498db
    for build in builds:
        submitter_id = build.get('submitted_by')
        submitter_mention = f"<@{submitter_id}>" if submitter_id else "Unknown User"
        try:
            if submitter_id:
                user = await bot.fetch_user(submitter_id)
                submitter_mention = user.mention if user else f"User ID: {submitter_id}"
        except Exception: # Handle cases where user might not be fetchable
            submitter_mention = f"User ID: {submitter_id}"
        perks = ', '.join(build.get('keyperks', [])) or '-'
        embed.add_field(name=build['name'], value=f"[Link]({build['link']})\nKey Perks: {perks}\nSubmitted by: {submitter_mention}", inline=False)
    await ctx.send(embeds=embed)


@build_group.subcommand(
    sub_cmd_name="remove",
    sub_cmd_description="Remove a saved build (requires 'Manage Server' permission)."
)
@slash_option(
    "name",
    description="The name of the build to remove",
    opt_type=OptionType.STRING,
    required=True,
    autocomplete=True
)
async def build_remove(ctx: SlashContext, name: str):
    # Check for 'Manage Server' permission or if the user is a bot manager/owner
    if not ctx.author.has_permission(Permissions.MANAGE_GUILD) and not is_bot_manager(int(ctx.author.id)):
        await ctx.send("You need 'Manage Server' permission or be a Bot Manager to use this command.", ephemeral=True)
        return

    try:
        with open(BUILDS_FILE, 'r', encoding='utf-8') as f:
            builds = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        await ctx.send("No builds saved yet or build file is corrupted.", ephemeral=True)
        return

    original_length = len(builds)
    # Find the build by name (case-insensitive)
    builds_filtered = [b for b in builds if b.get("name", "").lower() != name.lower()]

    if len(builds_filtered) == original_length:
        await ctx.send(f"Build '{name}' not found.", ephemeral=True)
        return

    try:
        with open(BUILDS_FILE, 'w', encoding='utf-8') as f:
            json.dump(builds_filtered, f, indent=2)
        await ctx.send(f"Build '{name}' removed successfully.", ephemeral=True)
    except Exception as e:
        logging.error(f"Error writing builds file after removing build: {e}")
        await ctx.send("An error occurred while trying to remove the build.", ephemeral=True)

@build_remove.autocomplete("name")
async def build_remove_autocomplete(ctx: SlashContext):
    try:
        with open(BUILDS_FILE, 'r', encoding='utf-8') as f:
            builds_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError): # Handle empty or corrupt file
        await ctx.send(choices=[])
        return # Ensure return after sending empty choices
    search_term = ctx.input_text.lower().strip() if ctx.input_text else ""
    matches = [build.get("name") for build in builds_data if build.get("name") and search_term in build.get("name", "").lower()]
    choices = [{"name": build_name, "value": build_name} for build_name in list(set(matches))[:25]] # Use set for unique names
    await ctx.send(choices=choices)


@slash_command(name="perk", description="Look up information about a specific New World perk.")
@slash_option(
    "perk_name",
    description="The name of the perk to look up",
    opt_type=OptionType.STRING,
    required=True,
    autocomplete=True
)
async def perk_command(ctx, perk_name: str):
    # all_perks_data = perks.load_perks_from_csv() # No longer load here
    if not ALL_PERKS_DATA:
        await ctx.send("Perk data is not loaded. Please try again later or contact an admin.", ephemeral=True)
        return

    perk_name_lower = perk_name.lower()
    if perk_name_lower not in ALL_PERKS_DATA:
        await ctx.send(f"Perk '{perk_name}' not found in the database.", ephemeral=True)
        return

    perk_info = ALL_PERKS_DATA[perk_name_lower]

    # Helper to get values safely, similar to the one in /nwdb
    def get_any_perk_info(data, keys, default):
        for k_csv in keys: # CSV headers can have varied casing
            for actual_key_in_data in data.keys():
                if actual_key_in_data.lower() == k_csv.lower():
                    if data[actual_key_in_data]:
                        return data[actual_key_in_data]
        return default

    name = get_any_perk_info(perk_info, ['name', 'perkname'], perk_name)
    description = get_any_perk_info(perk_info, ['description', 'desc'], 'No description available.')
    perk_type = get_any_perk_info(perk_info, ['type', 'perktype', 'category'], 'Unknown Type')
    icon_url = get_any_perk_info(perk_info, ['icon_url', 'icon'], None)
    perk_id = get_any_perk_info(perk_info, ['id', 'perkid'], None)

    embed = Embed(title=name, color=0x1ABC9C) # A teal color for perks
    if icon_url:
        embed.set_thumbnail(url=icon_url)

    embed.add_field(name="Description", value=description, inline=False)
    embed.add_field(name="Type", value=perk_type, inline=True)

    if perk_id:
        embed.add_field(name="NWDB Link", value=f"[View on NWDB](https://nwdb.info/db/perk/{perk_id})", inline=True)
    else:
        embed.add_field(name="ID", value="Not available", inline=True)

    embed.set_footer(text="Perk information from local data. Values may scale with Gear Score in-game.")
    await ctx.send(embeds=embed)

def _eval_perk_expression(expr_str: str, gs_multiplier_val: float) -> str:
    """
    Safely evaluates a perk expression string after substituting perkMultiplier.
    Example: expr_str = "2.4 * perkMultiplier", gs_multiplier_val = 1.45
    """
    try:
        # Replace perkMultiplier with its numeric value
        eval_str = expr_str.replace("perkMultiplier", str(gs_multiplier_val))

        # Define a safe environment for eval
        allowed_globals = {"__builtins__": {}}
        allowed_locals = {} # No extra functions needed for simple arithmetic like "2.4 * 1.45"

        result = eval(eval_str, allowed_globals, allowed_locals)

        if isinstance(result, float):
            if result.is_integer():
                return str(int(result))
            # Format to a reasonable number of decimal places, remove trailing zeros
            formatted_result = f"{result:.3f}".rstrip('0').rstrip('.')
            return formatted_result
        return str(result)
    except Exception as e:
        logging.warning(f"Could not evaluate perk expression '{expr_str}' with multiplier {gs_multiplier_val}: {e}")
        # Return the original expression part to indicate an issue or a placeholder error.
        return f"[EVAL_ERROR: {expr_str}]"

def scale_value_with_gs(base_value: Optional[str], gear_score: int = 725) -> str:
    """
    Scales numeric values within a perk description string based on Gear Score.
    Replaces placeholders like ${expression * perkMultiplier} or ${value} with their calculated/literal values.
    """
    if not base_value or '${' not in base_value:
        return base_value

    base_gs = 500  # Assume base values for perkMultiplier are for GS 500
    gs_multiplier = gear_score / base_gs

    def replace_match(match):
        expression_inside_braces = match.group(1) # Content within ${...}
        return _eval_perk_expression(expression_inside_braces, gs_multiplier)

    return re.sub(r'\$\{(.*?)\}', replace_match, base_value)

@perk_command.autocomplete("perk_name")
async def perk_autocomplete(ctx):
    # all_perks_data = perks.load_perks_from_csv() # No longer load here
    if not ALL_PERKS_DATA:
        await ctx.send(choices=[])
        return

    search_term = ctx.input_text.lower().strip() if ctx.input_text else ""
    
    # Match against the keys of all_perks_data (which are lowercase perk names)
    # Then retrieve the original display name from the 'name' field in the perk's data for the choice's name
    matches = []
    for perk_key_lower, perk_data_dict in ALL_PERKS_DATA.items():
        if search_term in perk_key_lower:
            # Try to get the original cased name for display
            display_name = perk_data_dict.get('name', perk_data_dict.get('Name', perk_key_lower.title()))
            matches.append({"name": display_name, "value": display_name}) # Send original cased name as value too

    # Ensure unique choices by name (in case of slight variations leading to same display name)
    # and limit to 25
    unique_matches = []
    seen_names = set()
    for match in matches:
        if match["name"] not in seen_names:
            unique_matches.append(match)
            seen_names.add(match["name"])
        if len(unique_matches) >= 25:
            break
            
    await ctx.send(choices=unique_matches)


@slash_command(name="about", description="Show information about Ina's New World Bot.")
async def about_command(ctx):
    embed = Embed(
        title="About Ina's New World Bot",
        description="Your friendly companion for all things Aeternum!",
        color=0x7289DA  # Discord Blurple
    )
    embed.add_field(
        name="Version",
        value=f"`{__version__}`",
        inline=True
    )
    embed.add_field(
        name="Creator",
        value="This bot was lovingly crafted by <@157968227106947072>.",
        inline=True # Changed to true to align better with version
    )
    embed.add_field(
        name="Credits & Data Sources",
        value="• Item and perk data often references [NWDB.info](https://nwdb.info).\n"
              "• Build functionality integrates with [NW-Buddy.de](https://nw-buddy.de).",
        inline=False
    )
    embed.set_footer(text="Ina's New World Bot is a fan-made project and is not affiliated with Amazon Games or New World.")
    await ctx.send(embeds=embed)

async def _perform_update_and_restart(slash_ctx: Optional[SlashContext] = None):
    """
    Handles the bot update process: executes the update script and stops the bot for restart.
    If slash_ctx is provided, sends feedback to the command invoker.
    Returns True if update script succeeded and bot stop was initiated, False otherwise.
    """
    # Determine OS and script details
    current_os = platform.system().lower()
    script_name = ""
    executable = ""

    if "windows" in current_os:
        script_name = "update_bot.ps1"
        executable = "powershell.exe"
        script_args = ['-ExecutionPolicy', 'Bypass', '-File']
    elif "linux" in current_os:
        script_name = "update_bot.sh"
        executable = "/bin/bash" # or "bash" if it's in PATH
        script_args = [] # No special args needed before the script path for bash
    else:
        await ctx.send(f"Unsupported operating system for automatic updates: {current_os}", ephemeral=True)
        return

    # Construct the path to the update script
    # Assumes main.py and the update script are in the same directory (the Git repo root).
    script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), script_name))

    if not os.path.exists(script_path):
        error_msg = f"Update script not found at: {script_path}"
        logging.error(error_msg)
        if slash_ctx:
            await slash_ctx.send(f"Error: Update script not found at the expected location: `{script_path}`.", ephemeral=True)
        return False

    initiator_desc = "Automatic update check"
    if slash_ctx and slash_ctx.author:
        initiator_desc = f"User {slash_ctx.author.username} ({slash_ctx.author.id})"

    try:
        logging.info(f"{initiator_desc} initiated bot update using {executable} with script: {script_path}")
        # The script (e.g., update_bot.sh or update_bot.ps1) is responsible for the actual Git operations,
        # including how updates are fetched (e.g., git pull, git reset --hard for force updates).
        # Using asyncio.create_subprocess_exec for non-blocking execution
        # Full command: executable *script_args script_path
        process = await asyncio.create_subprocess_exec(
            executable,
            *script_args, # Unpack arguments like -ExecutionPolicy Bypass -File
            script_path,  # The script itself is the last argument here
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate() # Wait for the script to complete

        stdout_str = stdout.decode('utf-8', errors='ignore')
        stderr_str = stderr.decode('utf-8', errors='ignore')

        if slash_ctx: # Send detailed feedback if initiated by command
            response_message = f"🚀 **Update Script Execution ({current_os.capitalize()})** 🚀\n"
            if process.returncode == 0:
                response_message += "✅ Script executed successfully.\n"
            else:
                response_message += f"⚠️ Script finished with exit code: {process.returncode}.\n"
            
            max_log_section_length = 850 # Max length for each log section

            if stdout_str:
                response_message += f"**Output:**\n```\n{stdout_str[:max_log_section_length]}\n```\n" # Using generic ```
                if len(stdout_str) > max_log_section_length:
                    response_message += f"... (output truncated)\n"
            if stderr_str:
                response_message += f"**Errors:**\n```\n{stderr_str[:max_log_section_length]}\n```\n" # Using generic ```
                if len(stderr_str) > max_log_section_length:
                    response_message += f"... (errors truncated)\n"
            
            if process.returncode == 0:
                response_message += "\n✅ **Updates pulled. Attempting to apply by restarting the bot...**\n"
                response_message += "ℹ️ The bot will shut down. An external process manager (e.g., PM2, systemd, Docker restart policy) is required to bring it back online with the updates."
            else:
                response_message += "\n❌ **Update script failed. Bot will not restart.**"

            if len(response_message) > 2000:
                response_message = (f"🚀 Update script finished with exit code: {process.returncode}. "
                                    f"Logs were too long to display here. Please check the console/logs. ")
                if process.returncode == 0:
                    response_message += "Bot will attempt to restart to apply updates."
                else:
                    response_message += "Bot will not restart."
            await slash_ctx.send(response_message, ephemeral=True)

        if process.returncode == 0:
            logging.info(f"Update script successful for {initiator_desc}. Stopping bot to apply updates.")
            if slash_ctx: await asyncio.sleep(3) # Ensure message is sent if slash_ctx exists
            await bot.stop()
            if not slash_ctx: # Log for automatic update
                logging.warning(f"Automatic update successful. Bot has been stopped for restart by process manager.")
            return True
        else:
            log_msg = f"Update script failed for {initiator_desc} with exit code {process.returncode}."
            if stdout: log_msg += f" Stdout: {stdout.decode(errors='ignore')}"
            if stderr: log_msg += f" Stderr: {stderr.decode(errors='ignore')}"
            logging.error(log_msg)
            if not slash_ctx: # Log for automatic update failure
                 logging.error(f"Automatic update failed. Script exit code: {process.returncode}.")
            return False
    except Exception as e:
        error_msg = f"An error occurred while {initiator_desc} tried to run update script '{script_name}': {e}"
        logging.error(error_msg, exc_info=True)
        if slash_ctx:
            await slash_ctx.send(error_msg, ephemeral=True)
        return False

# --- Bot Management Commands ---
@slash_command(name="manage", description="Manage bot operations (restricted).")
async def manage_group(ctx: SlashContext):
    """Base command for bot management."""
    pass

@manage_group.subcommand(
    sub_cmd_name="update",
    sub_cmd_description="Pulls updates from GitHub and restarts the bot (Owner only)."
)
async def manage_update(ctx: SlashContext):
    if ctx.author.id != OWNER_ID:
        await ctx.send("You do not have permission to use this command.", ephemeral=True)
        return

    await ctx.defer(ephemeral=True) # Acknowledge interaction, make response visible only to user
    await _perform_update_and_restart(slash_ctx=ctx)

@manage_group.subcommand(
    sub_cmd_name="restart",
    sub_cmd_description="Shuts down the bot for manual restart (Bot Owner/Manager only)."
)
async def manage_restart(ctx: SlashContext):
    if not is_bot_manager(int(ctx.author.id)) and ctx.author.id != OWNER_ID:
        await ctx.send("You do not have permission to use this command.", ephemeral=True)
        return

    guild_info = "a Direct Message"
    if ctx.guild:
        guild_info = f"guild {ctx.guild.name} ({ctx.guild.id})"

    logging.info(f"Restart command initiated by {ctx.author.username} ({ctx.author.id}) in {guild_info}.")

    await ctx.send(
        "✅ Bot shutdown command acknowledged. "
        "The bot process will now attempt to stop.\n"
        "ℹ️ **A manual restart of the bot's process on the server is required for it to come back online.**",
        ephemeral=True
    )
    # Gracefully stop the bot
    # Note: This stops the Python script. An external process manager (systemd, PM2, Docker, etc.)
    # or a wrapper script is needed to actually restart the bot process.
    await bot.stop()

# --- Settings Commands ---
@slash_command(name="settings", description="Manage bot settings (requires permissions).")
async def settings(ctx: SlashContext):
    """Base command for settings. Discord will typically show subcommands."""
    # This function body can be left empty or provide a generic help message
    # if called directly, though usually users will invoke subcommands.
    pass

@settings.subcommand(sub_cmd_name="permit", sub_cmd_description="Grants a user bot management permissions.")
@slash_option("user", "The user to grant permissions to.", opt_type=OptionType.USER, required=True)
async def settings_permit_subcommand(ctx: SlashContext, user: User): # Renamed to avoid conflict if settings was a class
    if not ctx.author.has_permission(Permissions.ADMINISTRATOR) and ctx.author.id != OWNER_ID:
        await ctx.send("You need Administrator permissions or be the Bot Owner to use this command.", ephemeral=True)
        return

    if add_bot_manager(int(user.id)):
        await ctx.send(f"✅ {user.mention} has been granted bot management permissions.", ephemeral=True)
    else:
        await ctx.send(f"ℹ️ {user.mention} already has bot management permissions.", ephemeral=True)

@settings.subcommand(sub_cmd_name="unpermit", sub_cmd_description="Revokes a user's bot management permissions.")
@slash_option("user", "The user to revoke permissions from.", opt_type=OptionType.USER, required=True)
async def settings_unpermit_subcommand(ctx: SlashContext, user: User): # Renamed
    if not ctx.author.has_permission(Permissions.ADMINISTRATOR) and ctx.author.id != OWNER_ID:
        await ctx.send("You need Administrator permissions or be the Bot Owner to use this command.", ephemeral=True)
        return

    if int(user.id) == OWNER_ID:
        await ctx.send("🚫 The bot owner's permissions cannot be revoked.", ephemeral=True)
        return

    if remove_bot_manager(int(user.id)):
        await ctx.send(f"✅ {user.mention}'s bot management permissions have been revoked.", ephemeral=True)
    else:
        await ctx.send(f"ℹ️ {user.mention} does not have bot management permissions.", ephemeral=True)

@settings.subcommand(sub_cmd_name="listmanagers", sub_cmd_description="Lists users with bot management permissions.")
async def settings_listmanagers_subcommand(ctx: SlashContext): # Renamed
    if not ctx.author.has_permission(Permissions.ADMINISTRATOR) and not is_bot_manager(int(ctx.author.id)) and ctx.author.id != OWNER_ID :
        await ctx.send("You need Administrator permissions or be a Bot Manager/Owner to use this command.", ephemeral=True)
        return

    managers = load_bot_managers()
    embed = Embed(title="👑 Bot Managers 👑", color=0xFFD700) # Gold color

    owner_user = await bot.fetch_user(OWNER_ID)
    if owner_user:
        embed.add_field(name="Bot Owner (Implicit Manager)", value=owner_user.mention, inline=False)
    else:
        embed.add_field(name="Bot Owner (Implicit Manager)", value=f"ID: {OWNER_ID} (User not found)", inline=False)

    if managers:
        manager_mentions = []
        for manager_id in managers:
            if manager_id == OWNER_ID: continue # Skip owner if already listed
            try:
                user = await bot.fetch_user(manager_id)
                manager_mentions.append(user.mention if user else f"ID: {manager_id} (User not found)")
            except Exception:
                manager_mentions.append(f"ID: {manager_id} (Error fetching user)")
        embed.add_field(name="Permitted Managers", value="\n".join(manager_mentions) if manager_mentions else "No additional managers permitted.", inline=False)
    else:
        embed.add_field(name="Permitted Managers", value="No additional managers permitted.", inline=False)
    await ctx.send(embeds=embed, ephemeral=True)


# Refactored welcome messages settings command
@settings.subcommand(
    sub_cmd_name="welcomemessages", 
    sub_cmd_description="Manage welcome messages for new members (enable/disable/status)."
)
@slash_option(
    name="action",
    description="The action to perform for welcome messages.",
    opt_type=OptionType.STRING,
    required=True,
    choices=[
        {"name": "Enable Welcome Messages", "value": "enable"},
        {"name": "Disable Welcome Messages", "value": "disable"},
        {"name": "Show Welcome Message Status", "value": "status"},
    ]
)
@slash_option(
    "channel",
    "The text channel for welcome messages (required if action is 'enable').",
    opt_type=OptionType.CHANNEL,
    required=False, # Optional at API level, checked in code
    channel_types=[ChannelType.GUILD_TEXT]
)
async def settings_welcomemessages_manager(ctx: SlashContext, action: str, channel: Optional[GuildText] = None):
    if not ctx.author.has_permission(Permissions.MANAGE_GUILD) and not is_bot_manager(int(ctx.author.id)):
        await ctx.send("You need 'Manage Server' permission or be a Bot Manager/Owner to use this command.", ephemeral=True)
        return
    if not ctx.guild:
        await ctx.send("This command can only be used in a server.", ephemeral=True)
        return

    action = action.lower() # Normalize action string

    if action == "enable":
        if not channel:
            await ctx.send("A channel is required to enable welcome messages. Please specify a channel.", ephemeral=True)
            return
        save_welcome_setting(str(ctx.guild.id), True, str(channel.id))
        await ctx.send(f"✅ Welcome messages are now **enabled** and will be sent to {channel.mention}.", ephemeral=True)
    elif action == "disable":
        save_welcome_setting(str(ctx.guild.id), False, None)
        await ctx.send("✅ Welcome messages are now **disabled** for this server.", ephemeral=True)
    elif action == "status":
        setting = get_welcome_setting(str(ctx.guild.id))
        if setting and setting.get("enabled") and setting.get("channel_id"):
            try:
                welcome_channel_obj = await bot.fetch_channel(int(setting['channel_id']))
                await ctx.send(f"ℹ️ Welcome messages are **enabled** and set to channel {welcome_channel_obj.mention}.", ephemeral=True)
            except Exception:
                await ctx.send(f"ℹ️ Welcome messages are **enabled** and set to channel ID `{setting['channel_id']}` (channel might be deleted or inaccessible).", ephemeral=True)
        else:
            await ctx.send("ℹ️ Welcome messages are currently **disabled** for this server.", ephemeral=True)
    else:
        # This case should ideally not be reached if choices are enforced by Discord
        await ctx.send("Invalid action specified. Please use 'enable', 'disable', or 'status'.", ephemeral=True)

# Refactored logging settings command
@settings.subcommand(
    sub_cmd_name="logging", 
    sub_cmd_description="Manage server activity logging (enable/disable/status)."
)
@slash_option(
    name="action",
    description="The action to perform for server activity logging.",
    opt_type=OptionType.STRING,
    required=True,
    choices=[
        {"name": "Enable Logging", "value": "enable"},
        {"name": "Disable Logging", "value": "disable"},
        {"name": "Show Logging Status", "value": "status"},
    ]
)
@slash_option(
    "channel",
    "The text channel for logs (required if action is 'enable').",
    opt_type=OptionType.CHANNEL,
    required=False, # Optional at API level, checked in code
    channel_types=[ChannelType.GUILD_TEXT]
)
async def settings_logging_manager(ctx: SlashContext, action: str, channel: Optional[GuildText] = None):
    if not ctx.author.has_permission(Permissions.MANAGE_GUILD) and not is_bot_manager(int(ctx.author.id)):
        await ctx.send("You need 'Manage Server' permission or be a Bot Manager/Owner to use this command.", ephemeral=True)
        return
    if not ctx.guild:
        await ctx.send("This command can only be used in a server.", ephemeral=True)
        return
    
    action = action.lower() # Normalize action string

    if action == "enable":
        if not channel:
            await ctx.send("A channel is required to enable logging. Please specify a channel.", ephemeral=True)
            return
        save_logging_setting(str(ctx.guild.id), True, str(channel.id))
        await ctx.send(f"✅ Server activity logging is now **enabled** and will be sent to {channel.mention}.", ephemeral=True)
    elif action == "disable":
        save_logging_setting(str(ctx.guild.id), False, None)
        await ctx.send("✅ Server activity logging is now **disabled** for this server.", ephemeral=True)
    elif action == "status":
        setting = get_logging_setting(str(ctx.guild.id))
        if setting and setting.get("enabled") and setting.get("channel_id"):
            try:
                log_channel_obj = await bot.fetch_channel(int(setting['channel_id']))
                await ctx.send(f"ℹ️ Server activity logging is **enabled** and set to channel {log_channel_obj.mention}.", ephemeral=True)
            except Exception:
                await ctx.send(f"ℹ️ Server activity logging is **enabled** and set to channel ID `{setting['channel_id']}` (channel might be deleted or inaccessible).", ephemeral=True)
        else:
            await ctx.send("ℹ️ Server activity logging is currently **disabled** for this server.", ephemeral=True)
    else:
        # This case should ideally not be reached if choices are enforced by Discord
        await ctx.send("Invalid action specified. Please use 'enable', 'disable', or 'status'.", ephemeral=True)

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

# Mention handler
@bot.event()
async def on_message_create(event_name: str, event_data): # event_data is typically the Message object
    # In v4 style, the second argument is usually the primary payload (e.g., Message object)
    message = event_data 
    
    if not message:
        return
    # Ensure message is a Message object, not a string or other type if dispatch is unexpected
    if not isinstance(message, Message):
        logging.warning(f"on_message_create received unexpected event_data type: {type(event_data)}. Value: {event_data}")
        return

    author = getattr(message, "author", None)
    if not author or getattr(author, "bot", False):
        return
    bot_self = getattr(bot, "me", None) or getattr(bot, "user", None)
    if not bot_self or not hasattr(bot_self, "id"):
        return
    bot_id = str(getattr(bot_self, "id", None))
    mentions = getattr(message, "mentions", []) or []
    mentioned_ids = {str(m.id) for m in mentions if hasattr(m, 'id')}
    content = getattr(message, "content", "") or getattr(message, "text", "")
    if bot_id in mentioned_ids or f"<@{bot_id}>" in content:
        channel_id = getattr(message, "channel_id", None)
        if channel_id:
            channel = await bot.fetch_channel(channel_id)
            # Only send if channel supports send (TextChannel, not GuildForum, GuildCategory, or None)
            if channel and hasattr(channel, 'send') and isinstance(channel, TextChannel): # More robust check
                await channel.send(random.choice(SILLY_MENTION_RESPONSES))

async def _log_server_activity(guild_id: str, embed: Embed, text_message: Optional[str] = None):
    """Helper function to send log messages to the configured log channel."""
    if not guild_id:
        return

    log_settings = get_logging_setting(str(guild_id))
    if log_settings and log_settings.get("enabled") and log_settings.get("channel_id"):
        log_channel_id = log_settings["channel_id"]
        try:
            log_channel = await bot.fetch_channel(int(log_channel_id))
            if log_channel and isinstance(log_channel, TextChannel): # Ensure it's a text channel
                if not embed.timestamp: # Add timestamp if not already set
                    embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
                await log_channel.send(content=text_message, embeds=embed)
            else:
                logging.warning(f"Log channel {log_channel_id} in guild {guild_id} is not a valid text channel or not found.")
        except Permissions.Missing:
            logging.error(f"Missing permissions to send log message in channel {log_channel_id} for guild {guild_id}.")
        except Exception as e:
            logging.error(f"Failed to send log message to channel {log_channel_id} in guild {guild_id}: {e}", exc_info=True)



@bot.event()
async def on_guild_member_add(event_name: str, member: Member):
    """Handles new member joins and sends a welcome message if configured."""
    if not member.guild:
        return # Should not happen for this event, but good practice

    # Defensive check if member is not actually a Member object
    if not isinstance(member, Member):
        logging.error(f"on_guild_member_add received non-Member object for member: {type(member)}. Value: {member}")
        # Attempt to fetch member if 'member' was an ID, though this is unlikely for this event
        # This part is highly speculative and depends on what 'member' might be if not a Member object.
        return

    guild_id_str = str(member.guild.id)
    settings = get_welcome_setting(guild_id_str)

    if settings and settings.get("enabled") and settings.get("channel_id"):
        channel_id = settings["channel_id"]
        try:
            # Ensure channel_id is an int for fetch_channel if it expects int
            channel = await bot.fetch_channel(int(channel_id))
            if channel and isinstance(channel, TextChannel): # Check if it's a text channel
                welcome_message = random.choice(NEW_WORLD_WELCOME_MESSAGES).format(
                    member_mention=member.mention,
                    guild_name=member.guild.name
                )
                await channel.send(welcome_message)
                logging.info(f"Sent welcome message to {member.username} in guild {member.guild.name} ({guild_id_str}), channel {channel.name} ({channel_id}).")
            else:
                logging.warning(f"Welcome message channel {channel_id} in guild {guild_id_str} is not a valid text channel or not found.")
        except Exception as e:
            logging.error(f"Failed to send welcome message in guild {guild_id_str}, channel {channel_id}: {e}", exc_info=True)

# --- Server Activity Logging Events ---
@bot.event()
async def on_message_delete(event_name: str, message: Message):
    if not isinstance(message, Message):
        logging.warning(f"on_message_delete received non-Message object: {type(message)}. Value: {message}")
        return
        
    # Original check:
    if not getattr(message, 'guild', None): # Only log guild messages
        return

    # Message content might not be available if not cached or intent is missing
    content = message.content if message.content else "[Content not available or message was an embed]"
    if len(content) > 1000: # Truncate long messages
        content = content[:1000] + "..."

    embed = Embed(
        title="🗑️ Message Deleted",
        color=0xFF0000, # Red
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    embed.add_field(name="Author", value=f"{message.author.mention} (`{message.author.id}`)", inline=True)
    embed.add_field(name="Channel", value=message.channel.mention, inline=True)
    embed.add_field(name="Content", value=f"```{content}```", inline=False)
    if message.attachments:
        embed.add_field(name="Attachments", value=f"{len(message.attachments)} attachment(s)", inline=True)
    embed.set_footer(text=f"Message ID: {message.id}")

    await _log_server_activity(str(message.guild.id), embed)

@bot.event()
async def on_message_update(event_name: str, before: Optional[Message] = None, after: Optional[Message] = None):
    # Defensive checks for types, as the original error implies _args might be empty for this event
    if not after:
        logging.warning(f"on_message_update for event '{event_name}' called without 'after' message. Before: {before}. This may indicate a library dispatch issue or an event without an 'after' payload.")
        return
    
    # Ensure 'after' is a Message object if it was provided
    if not isinstance(after, Message): # This check might be redundant if the above 'if not after:' catches it.
        logging.error(f"on_message_update: 'after' (value: {after}) is not a Message object. Type: {type(after)}. This indicates a library dispatch issue.")
        return
    if before is not None and not isinstance(before, Message):
        logging.warning(f"on_message_update: 'before' is not None and not a Message object. Type: {type(before)}, Value: {before}")
        # Depending on library behavior, 'before' might be None if not in cache.
        # If it's something else unexpected, it's an issue.

    if not getattr(after, 'guild', None) or not getattr(after, 'author', None) or getattr(after.author, 'bot', True): # Only log guild messages from users
        return
    if before and getattr(before, 'content', None) == getattr(after, 'content', None) and not (getattr(before, 'embeds', []) != getattr(after, 'embeds', [])): # Ignore if only embeds changed by bot itself or no actual content change
        return

    old_content = before.content if before and before.content else "[Content not available or was an embed]"
    new_content = after.content if after.content else "[Content not available or is an embed]"

    if len(old_content) > 450: old_content = old_content[:450] + "..."
    if len(new_content) > 450: new_content = new_content[:450] + "..."

    embed = Embed(
        title="✏️ Message Edited",
        description=f"Jump to Message",
        color=0x007FFF, # Blue
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    embed.add_field(name="Author", value=f"{after.author.mention} (`{after.author.id}`)", inline=True)
    embed.add_field(name="Channel", value=after.channel.mention, inline=True)
    embed.add_field(name="Before", value=f"```{old_content}```", inline=False)
    embed.add_field(name="After", value=f"```{new_content}```", inline=False)
    embed.set_footer(text=f"Message ID: {after.id}")

    await _log_server_activity(str(after.guild.id), embed)

@bot.event()
async def on_guild_member_remove(event_name: str, member: Member):
    if not isinstance(member, Member):
        logging.error(f"on_guild_member_remove received non-Member object: {type(member)}. Value: {member}")
        return

    if not getattr(member, 'guild', None):
        return

    embed = Embed(
        title="🚶 Member Left",
        description=f"{member.mention} (`{member.username}#{member.discriminator}` | `{member.id}`)",
        color=0xFFA500, # Orange
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    if getattr(member, 'avatar', None):
      embed.set_thumbnail(url=member.avatar.url)

    await _log_server_activity(str(member.guild.id), embed)

@bot.event()
async def on_guild_ban(event_name: str, guild_id: str, user: User): # Assuming guild_id and user are passed
    guild = await bot.fetch_guild(guild_id) # Fetch guild if only ID is provided
    if not guild: return

    if not isinstance(user, User):
        logging.error(f"on_guild_ban received non-User object: {type(user)}. Value: {user}")
        return

    embed = Embed(
        title="🔨 Member Banned",
        description=f"{user.mention} (`{user.username}#{user.discriminator}` | `{user.id}`)",
        color=0xDC143C, # Crimson
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    if getattr(user, 'avatar', None):
        embed.set_thumbnail(url=user.avatar.url)
    await _log_server_activity(str(guild.id), embed)

@bot.event()
async def on_guild_unban(event_name: str, guild_id: str, user: User):
    guild = await bot.fetch_guild(guild_id)
    if not guild: return

    if not isinstance(user, User):
        logging.error(f"on_guild_unban received non-User object: {type(user)}. Value: {user}")
        return

    embed = Embed(
        title="🤝 Member Unbanned",
        description=f"{user.mention} (`{user.username}#{user.discriminator}` | `{user.id}`)",
        color=0x32CD32, # LimeGreen
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    if getattr(user, 'avatar', None):
        embed.set_thumbnail(url=user.avatar.url)
    await _log_server_activity(str(guild.id), embed)

@bot.event()
async def on_guild_role_create(event_name: str, role: Role):
    if not isinstance(role, Role):
        logging.error(f"on_guild_role_create received non-Role object: {type(role)}. Value: {role}")
        return

    embed = Embed(
        title="✨ Role Created",
        description=f"Role: {role.mention} (`{role.name}` | `{role.id}`)",
        color=0x00FF00, # Green
    )
    if hasattr(role, 'guild') and role.guild: # Ensure role has guild context
        await _log_server_activity(str(role.guild.id), embed)

@bot.event()
async def on_guild_role_delete(event_name: str, role: Role): 
    if not isinstance(role, Role):
        logging.error(f"on_guild_role_delete received non-Role object: {type(role)}. Value: {role}")
        return

    embed = Embed(
        title="🗑️ Role Deleted",
        description=f"Role Name: `{role.name}` (ID: `{role.id}`)",
        color=0xFF4500, # OrangeRed
    )
    if hasattr(role, 'guild') and role.guild: # Ensure role has guild context
        await _log_server_activity(str(role.guild.id), embed)


# --- New World funny status (RPC) rotation ---
NW_FUNNY_STATUSES = [
    {"name": "Terror Turkey", "state": "Being hunted... or hunting?"},
    {"name": "Hemp for... ropes", "state": "Medicinal purposes, I swear!"},
    {"name": "Fishing in Aeternum", "state": "Wonder if fish count as currency?"},
    {"name": "the wilderness", "state": "Lost. Send cookies!"},
    {"name": "with optional bosses", "state": "They weren't optional."},
    {"name": "Tax negotiations", "state": "With the governor."},
    {"name": "Inventory Tetris", "state": "And losing again."},
    {"name": "Azoth management", "state": "Critically low. On foot?"},
    {"name": "Logging", "state": "The trees know my name."},
    {"name": "Peace mode", "state": "Just pretending to be relaxed."},
    {"name": "Crafting madness", "state": "Art or junk?"},
    {"name": "Expeditions", "state": "Healer has aggro. Classic."},
    {"name": "PvP", "state": "Looking for a fight, finds the floor."},
    {"name": "Open World PvP", "state": "'Fairplayed' by a 5-man group."},
    {"name": "Siege Wars", "state": "Popcorn for the lag show."},
    {"name": "Ganking 101", "state": "Plans epic, gets ganked."},
    {"name": "PvP with 1 HP", "state": "'Strategy', not luck."},
    {"name": "Outpost Rush", "state": "Baroness Nash > Players."},
    {"name": "Bashing skeletons", "state": "They have a bone to pick."},
    {"name": "Dungeon Runs", "state": "Who pulled again?!"},
    {"name": "Elite Zones", "state": "Everything wants to eat me."},
    {"name": "Questing", "state": "'Kill 10 boars'. Yawn."},
    {"name": "Corruption Portals", "state": "Tentacle party!"},
    {"name": "Hardcore Aeternum", "state": "Died to a level 5 wolf."},
    {"name": "Hardcore Hiking", "state": "3h to Everfall. On foot."},
    {"name": "Hardcore Loot Drop", "state": "Everything gone. Thanks, Prowler."},
    {"name": "Hardcore with 1 Life", "state": "Trips. Game Over."},
    {"name": "Bot-Spotting", "state": "Player or lumberjack bot?"},
    {"name": "Resource Routes", "state": "Efficient. Or a bot."},
    {"name": "Combat Bots", "state": "Only light attacks. Always."},
    {"name": "GPS-guided Players", "state": "No deviation from the path."},
    {"name": "Silent Teammates", "state": "Focused or bot?"}
]

BOT_INVITE_URL = "https://discord.com/oauth2/authorize?client_id=1368579444209352754&scope=bot+applications.commands&permissions=8"

async def rotate_funny_presence(bot, interval=60):
    await bot.wait_until_ready()
    while True:
        status = random.choice(NW_FUNNY_STATUSES)
        funny_status = f"{status['name']} – {status['state']}"
        activity_buttons = [
            {
                "label": "Add Ina's Bot to your Server",
                "url": BOT_INVITE_URL,
            }
        ]
        try:
            await bot.change_presence(activity=Activity(name=funny_status, type=ActivityType.GAME, buttons=activity_buttons))
        except Exception as e:
            logging.warning(f"Failed to set presence: {e}")
        await asyncio.sleep(interval)


async def check_for_updates():
    """Periodically checks GitHub for new bot releases and logs a notification if found."""
    await bot.wait_until_ready()
    logging.info(f"Ina's New World Bot version: {__version__} starting update checks.")
    while True:
        try:
            headers = {
                "Accept": "application/vnd.github.v3+json",
                # "User-Agent": "InaDiscordBotUpdateChecker/1.0" # Optional: Good practice for API requests
            }
            # Fetch the VERSION file from the main branch
            response = requests.get(GITHUB_VERSION_FILE_URL, headers=headers, timeout=15) # headers might not be strictly needed for raw.githubusercontent

            if response.status_code == 404:
                logging.info(f"VERSION file not found on main branch at {GITHUB_VERSION_FILE_URL}. Update check skipped.")
            elif response.status_code == 200:
                latest_version_str = response.text.strip() # The content of the VERSION file
                # Link to the main branch for update instructions/source
                update_source_url = f"https://github.com/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/tree/main"

                if latest_version_str:
                    current_v = packaging.version.parse(__version__)
                    latest_v = packaging.version.parse(latest_version_str)

                    logging.debug(f"Update Check: Current bot version: {current_v}, Latest version on main branch: {latest_v}")

                    if latest_v > current_v:
                        logging.warning(
                            f"🎉 A new version of Ina's New World Bot is available: {latest_v} "
                            f"(current: {current_v}). Attempting automatic update and restart. Source: {update_source_url}"
                        )
                        await _perform_update_and_restart() # Automatic update, no context
                    else:
                        logging.info("Bot is up to date with the version on the main branch.")
                else:
                    logging.warning(f"VERSION file at {GITHUB_VERSION_FILE_URL} is empty or invalid.")
            else:
                logging.error(
                    f"Failed to fetch latest release info from GitHub. Status: {response.status_code}, "
                    f"Response: {response.text[:200]}"
                )
        except requests.exceptions.RequestException as e:
            logging.error(f"Network error during GitHub update check: {e}")
        except packaging.version.InvalidVersion as e:
            logging.error(f"Error parsing version string during update check: {e}")
        except Exception as e:
            logging.error(f"An unexpected error occurred during GitHub update check: {e}", exc_info=True)
        
        await asyncio.sleep(UPDATE_CHECK_INTERVAL_SECONDS)

def load_all_game_data():
    """Loads all necessary game data from CSV files into global variables."""
    global ITEM_DATA, ALL_PERKS_DATA, ITEM_ID_TO_NAME_MAP
    logging.info("Starting to load game data...")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    items_csv_path = os.path.join(script_dir, 'items.csv')
    perks_csv_path = os.path.join(script_dir, 'perks.csv') # Assuming perks.csv is in the same directory

    ITEM_DATA = items.load_items_from_csv(items_csv_path)
    if not ITEM_DATA:
        logging.error(f"CRITICAL: Failed to load item_data from {items_csv_path}! Item-related commands will fail.")
        ITEM_DATA = {} # Ensure it's an empty dict if loading fails
        ITEM_ID_TO_NAME_MAP = {}
    else:
        logging.info(f"Successfully loaded {len(ITEM_DATA)} items from {items_csv_path}.")
        # Populate ITEM_ID_TO_NAME_MAP
        ITEM_ID_TO_NAME_MAP = {
            row.get('Item ID'): row.get('Name') # Assuming 'Name' is the original cased name column
            for row in ITEM_DATA.values()
            if row.get('Item ID') and row.get('Name')
        }
        logging.info(f"Successfully created ITEM_ID_TO_NAME_MAP with {len(ITEM_ID_TO_NAME_MAP)} entries.")

    ALL_PERKS_DATA = perks.load_perks_from_csv(perks_csv_path) # Pass the path for consistency
    if not ALL_PERKS_DATA:
        logging.error(f"CRITICAL: Failed to load all_perks_data from {perks_csv_path}! Perk-related commands will fail.")
        ALL_PERKS_DATA = {} # Ensure it's an empty dict
    else:
        logging.info(f"Successfully loaded {len(ALL_PERKS_DATA)} perks from {perks_csv_path}.")
    logging.info("Game data loading process complete.")

@bot.event()
async def on_ready():
    # load_all_game_data() # Moved to be called before bot.start()
    asyncio.create_task(rotate_funny_presence(bot, interval=60))
    asyncio.create_task(check_for_updates())
    logging.info(f"Ina is ready! Logged in as {bot.user.username} ({bot.user.id})")

if __name__ == "__main__":
    load_all_game_data() # Load data before starting the bot
    try:
        bot.start()
    except Exception as e:
        logging.error(f"Failed to start the bot: {e}")
