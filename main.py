import os
import sys
import random
import logging
import asyncio
import uuid
import math
import subprocess
import unicodedata
import re
import items
import perks # Import the new perks module
from interactions import Client, slash_command, slash_option, OptionType, Permissions, Embed, Activity, ActivityType
from typing import Optional
import packaging.version # For version comparison
from recipes import get_recipe, calculate_crafting_materials, RECIPES
import json
from bs4 import BeautifulSoup
import requests

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

__version__ = "0.1.4" # << SET YOUR BOT'S CURRENT VERSION HERE

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logging.getLogger("interactions").setLevel(logging.DEBUG)

bot_token = os.getenv("BOT_TOKEN")
if not bot_token:
    print("Error: BOT_TOKEN not found in .env file. Please make sure it is set.")
    sys.exit(1)

bot = Client(token=bot_token)

BUILDS_FILE = 'saved_builds.json'

# --- Update Checker Configuration ---
GITHUB_REPO_OWNER = "involvex"
GITHUB_REPO_NAME = "ina-discord-bot-" # Added trailing hyphen
# URL to a file on the main branch containing the version string (e.g., "0.1.1")
GITHUB_VERSION_FILE_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/main/VERSION"
UPDATE_CHECK_INTERVAL_SECONDS = 6 * 60 * 60  # Periodic check interval (e.g., every 6 hours)


@slash_command("ping", description="Check if the bot is online.")
async def ping(ctx):
    await ctx.send("Pong! Ina is online.")


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
        "builds": "Show a list of saved builds.",
        "removebuild": "Remove a saved build (requires 'Manage Server' permission).",
        "perk": "Look up information about a specific New World perk.",
        "about": "Show information about Ina's New World Bot."
    }
    if command and command.lower() in commands:
        await ctx.send(f"**/{command.lower().split()[0]}**: {commands[command.lower()]}") # Use split for commands with options in help
    else:
        help_text = "\n".join([f"**/{cmd}**: {desc}" for cmd, desc in commands.items()])
        await ctx.send(f"**Ina's New World Bot Commands:**\n{help_text}")


@slash_command("petpet", description="Give a New World petting ritual to a user!")
@slash_option("user", "The user to pet (Aeternum style)", opt_type=OptionType.USER, required=True)
async def petpet(ctx, user):
    await ctx.send(f"✨ {user.mention} receives a magical petpet ritual from the winds of Aeternum! 🐾")


@slash_command("calculate", description="Perform a calculation with New World magic!")
@slash_option("expression", "The mathematical expression to calculate", opt_type=OptionType.STRING, required=True)
async def calculate(ctx, expression: str):
    try:
        allowed_names = {k: v for k, v in math.__dict__.items() if not k.startswith("_")}
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        await ctx.send(f"🔮 The result of `{expression}` is `{result}`.")
    except Exception as e:
        await ctx.send(f"The arcane calculation failed: {e}", ephemeral=True)


@slash_command("nwdb", description="Look up items from New World Database.")
@slash_option("item_name", "The name of the item to look up", opt_type=OptionType.STRING, required=True, autocomplete=True)
async def nwdb(ctx, item_name: str):
    # Load items from CSV
    item_data = items.load_items_from_csv('items.csv')
    if not item_data:
        await ctx.send("Could not load item data.", ephemeral=True)
        return
    item_name_lower = item_name.lower()
    if item_name_lower not in item_data:
        await ctx.send(f"Item '{item_name}' not found in the database.", ephemeral=True)
        return
    item = item_data[item_name_lower]
    def get_any(item, keys, default):
        for k in keys:
            if k in item and item[k]:
                return item[k]
        return default
    name = get_any(item, ['name', 'Name', 'Item Name'], item_name)
    description = get_any(item, ['description', 'Description', 'Flavor Text'], 'No description available.')
    rarity = get_any(item, ['rarity', 'Rarity'], 'Unknown')
    tier = get_any(item, ['tier', 'Tier'], 'Unknown')
    icon_url = get_any(item, ['icon', 'Icon', 'Icon Path', 'icon_url'], None)
    # Build a NWDB-style embed
    embed = Embed()
    embed.title = name
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
    if get_recipe(item_name):
        embed.set_footer(text=f"Type /calculate_craft item_name:{item_name} amount:4 to calculate resources!")
    await ctx.send(embeds=embed)


@nwdb.autocomplete("item_name")
async def nwdb_autocomplete(ctx):
    # Provide autocomplete suggestions from items.csv
    item_data = items.load_items_from_csv('items.csv')
    if not item_data:
        await ctx.send(choices=[])
        return
    search_term = ctx.input_text.lower().strip() if ctx.input_text else ""
    matches = [name for name in item_data.keys() if search_term in name]
    # Discord allows max 25 choices
    choices = [{"name": name, "value": name} for name in list(matches)[:25]]
    await ctx.send(choices=choices)


@slash_command("calculate_craft", description="Calculate all resources needed to craft an item, including intermediates.")
@slash_option("item_name", "The name of the item to craft", opt_type=OptionType.STRING, required=True, autocomplete=True)
@slash_option("amount", "How many to craft", opt_type=OptionType.INTEGER, required=False)
async def calculate_craft(ctx, item_name: str, amount: int = 1):
    recipe = get_recipe(item_name)
    if not recipe:
        await ctx.send(f"No recipe found for '{item_name}'.", ephemeral=True)
        return
    # Show all resources, including intermediates
    all_materials = calculate_crafting_materials(item_name, amount or 1, include_intermediate=True)
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
    matches = [name for name in RECIPES.keys() if search_term in name]
    choices = [{"name": name.title(), "value": name} for name in list(matches)[:25]]
    await ctx.send(choices=choices)


@slash_command("recipe", description="Show the full recipe breakdown for a craftable item and track it.")
@slash_option("item_name", "The name of the item to show the recipe for", opt_type=OptionType.STRING, required=True, autocomplete=True)
async def recipe(ctx, item_name: str):
    from recipes import get_recipe, fetch_recipe_from_nwdb, track_recipe
    recipe = get_recipe(item_name)
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
    embed.add_field(name="Ingredients", value="\n".join(ing_lines) or "-", inline=False)
    await ctx.send(embeds=embed)


@recipe.autocomplete("item_name")
async def recipe_autocomplete(ctx):
    search_term = ctx.input_text.lower().strip() if ctx.input_text else ""
    # Load all items from CSV for autocomplete
    item_data = items.load_items_from_csv('items.csv')
    if not item_data:
        await ctx.send(choices=[])
        return
    matches = [name for name in item_data.keys() if search_term in name]
    choices = [{"name": name.title(), "value": name} for name in list(matches)[:25]]
    await ctx.send(choices=choices)


@slash_command("addbuild", description="Add a build from nw-buddy.de with a name and optional key perks.")
@slash_option("link", "The nw-buddy.de build link", opt_type=OptionType.STRING, required=True)
@slash_option("name", "A name for this build", opt_type=OptionType.STRING, required=True)
@slash_option("keyperks", "Comma-separated list of key perks (optional, paste from Perk stacks)", opt_type=OptionType.STRING, required=False)
async def addbuild(ctx, link: str, name: str, keyperks: str = None):
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
        builds = []
    builds.append({"name": name, "link": link, "keyperks": perks_list})
    with open(BUILDS_FILE, 'w', encoding='utf-8') as f:
        json.dump(builds, f, indent=2)
    await ctx.send(f"Build '{name}' added!", ephemeral=True)


@slash_command("builds", description="Show a list of saved builds.")
async def builds(ctx):
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
        perks = ', '.join(build.get('keyperks', [])) or '-'
        embed.add_field(name=build['name'], value=f"[Link]({build['link']})\nKey Perks: {perks}", inline=False)
    await ctx.send(embeds=embed)


@slash_command(
    "removebuild",
    description="Remove a saved build (requires 'Manage Server' permission).",
    default_member_permissions=Permissions.MANAGE_GUILD
)
@slash_option(
    "name",
    description="The name of the build to remove",
    opt_type=OptionType.STRING,
    required=True,
    autocomplete=True
)
async def removebuild(ctx, name: str):
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

@removebuild.autocomplete("name")
async def removebuild_autocomplete(ctx):
    try:
        with open(BUILDS_FILE, 'r', encoding='utf-8') as f:
            builds_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError): # Handle empty or corrupt file
        await ctx.send(choices=[])
        return
    search_term = ctx.input_text.lower().strip() if ctx.input_text else ""
    matches = [build.get("name") for build in builds_data if build.get("name") and search_term in build.get("name", "").lower()]
    choices = [{"name": build_name, "value": build_name} for build_name in list(set(matches))[:25]] # Use set for unique names
    await ctx.send(choices=choices)


@slash_command("perk", description="Look up information about a specific New World perk.")
@slash_option(
    "perk_name",
    description="The name of the perk to look up",
    opt_type=OptionType.STRING,
    required=True,
    autocomplete=True
)
async def perk_command(ctx, perk_name: str):
    all_perks_data = perks.load_perks_from_csv() # Using the function from perks.py
    if not all_perks_data:
        await ctx.send("Could not load perk data. Please check server logs.", ephemeral=True)
        return

    perk_name_lower = perk_name.lower()
    if perk_name_lower not in all_perks_data:
        await ctx.send(f"Perk '{perk_name}' not found in the database.", ephemeral=True)
        return

    perk_info = all_perks_data[perk_name_lower]

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

def scale_value_with_gs(base_value: str, gear_score: int = 725) -> str:
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
    all_perks_data = perks.load_perks_from_csv()
    if not all_perks_data:
        await ctx.send(choices=[])
        return

    search_term = ctx.input_text.lower().strip() if ctx.input_text else ""
    
    # Match against the keys of all_perks_data (which are lowercase perk names)
    # Then retrieve the original display name from the 'name' field in the perk's data for the choice's name
    matches = []
    for perk_key_lower, perk_data_dict in all_perks_data.items():
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


@slash_command("about", description="Show information about Ina's New World Bot.")
async def about_command(ctx):
    embed = Embed(
        title="About Ina's New World Bot",
        description="Your friendly companion for all things Aeternum!",
        color=0x7289DA  # Discord Blurple
    )
    embed.add_field(
        name="Creator",
        value="This bot was lovingly crafted by <@157968227106947072>.",
        inline=False
    )
    embed.add_field(
        name="Credits & Data Sources",
        value="• Item and perk data often references [NWDB.info](https://nwdb.info).\n"
              "• Build functionality integrates with [NW-Buddy.de](https://nw-buddy.de).",
        inline=False
    )
    embed.set_footer(text="Ina's New World Bot is a fan-made project and is not affiliated with Amazon Games or New World.")
    await ctx.send(embeds=embed)

# Mention handler
@bot.event()
async def on_message_create(event):
    message = getattr(event, "message", None) or getattr(event, "data", None)
    if not message:
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
            if channel and hasattr(channel, 'send') and channel.__class__.__name__ == 'TextChannel':
                await channel.send("👋 The winds of Aeternum greet you! Use `/help` to see my commands.")


# --- New World funny status (RPC) rotation ---
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
    {"name": "Hardcore Aeternum", "state": "An Level-5-Wolf gestorben."},
    {"name": "Hardcore-Wandern", "state": "3h nach Immerfall. Zu Fuß."},
    {"name": "Hardcore Loot Drop", "state": "Alles weg. Danke, Plünderer."},
    {"name": "Hardcore mit 1 Leben", "state": "Stolpert. Game Over."},
    {"name": "Bot-Spotting", "state": "Spieler oder Holzfäller-Bot?"},
    {"name": "Ressourcen-Routen", "state": "Effizient. Oder Bot."},
    {"name": "Kampf-Bots", "state": "Nur Light Attacks. Immer."},
    {"name": "GPS-gesteuerte Spieler", "state": "Keine Abweichung vom Pfad."},
    {"name": "stumme Mitspieler", "state": "Konzentriert oder Bot?"}
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
                            f"(current: {current_v}). Restart the bot to apply the update. Source: {update_source_url}"
                        )
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

@bot.event()
async def on_ready():
    asyncio.create_task(rotate_funny_presence(bot, interval=60))
    asyncio.create_task(check_for_updates())

if __name__ == "__main__":
    try:
        bot.start()
    except Exception as e:
        logging.error(f"Failed to start the bot: {e}")
