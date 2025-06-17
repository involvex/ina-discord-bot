import os
import sys
import random
import logging
import asyncio
import uuid
import math
import unicodedata
import re
import items
from interactions import Client, slash_command, slash_option, OptionType
from typing import Optional
from recipes import get_recipe, calculate_crafting_materials, RECIPES

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logging.getLogger("interactions").setLevel(logging.DEBUG)

DEBUG = True

bot_token = os.getenv("BOT_TOKEN")
if not bot_token:
    print("Error: BOT_TOKEN not found in .env file. Please make sure it is set.")
    sys.exit(1)

bot = Client(token=bot_token)


@slash_command("ping", description="Check if the bot is online.")
async def ping(ctx):
    await ctx.send("Pong! Ina is online.")


@slash_command("help", description="Show all available commands and their descriptions")
@slash_option("command", "Get detailed help for a specific command", opt_type=OptionType.STRING, required=False)
async def help_command(ctx, command: Optional[str] = None):
    commands = {
        "ping": "Check if the bot is online.",
        "petpet": "Give a New World petting ritual to a user!",
        "calculate": "Perform a calculation with New World magic!",
        "nwdb": "Look up items from New World Database.",
    }
    if command and command.lower() in commands:
        await ctx.send(f"**/{command.lower()}**: {commands[command.lower()]}")
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
    from interactions import Embed
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


@slash_command("recipe", description="Show the full recipe breakdown for a craftable item.")
@slash_option("item_name", "The name of the item to show the recipe for", opt_type=OptionType.STRING, required=True, autocomplete=True)
async def recipe(ctx, item_name: str):
    recipe = get_recipe(item_name)
    if not recipe:
        await ctx.send(f"No recipe found for '{item_name}'.", ephemeral=True)
        return
    from interactions import Embed
    embed = Embed()
    embed.title = f"Recipe: {item_name.title()}"
    embed.color = 0x9b59b6
    embed.add_field(name="Station", value=recipe.get("station", "-"), inline=True)
    embed.add_field(name="Skill", value=f"{recipe.get('skill', '-')}", inline=True)
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
    matches = [name for name in RECIPES.keys() if search_term in name]
    choices = [{"name": name.title(), "value": name} for name in list(matches)[:25]]
    await ctx.send(choices=choices)


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

async def rotate_funny_presence(bot, interval=60):
    await bot.wait_until_ready()
    while True:
        status = random.choice(NW_FUNNY_STATUSES)
        funny_status = f"{status['name']} – {status['state']}"
        await bot.change_presence(
            activity={
                "name": funny_status,
                "type": 0  # 0 = Playing
            }
        )
        await asyncio.sleep(interval)


@bot.event()
async def on_ready():
    asyncio.create_task(rotate_funny_presence(bot, interval=60))


if __name__ == "__main__":
    try:
        bot.start()
    except Exception as e:
        logging.error(f"Failed to start the bot: {e}")
