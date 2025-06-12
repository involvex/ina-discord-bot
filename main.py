import os
import sys
import asyncio
import logging
import uuid
import items
import recipes
from thefuzz import process
from dotenv import load_dotenv
from typing import Optional
import unicodedata
import re
import random
import aiohttp

import interactions
from interactions import (
    Client,
    listen,
    slash_command,
    BrandColours,
    slash_option,
    File,
    ButtonStyle,
    ModalContext
)

# Load environment variables from .env file
load_dotenv()

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
except ImportError:
    print("Failed to import watchdog. Code reloading will not work.")
    Observer = None
    FileSystemEventHandler = None

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logging.getLogger("interactions").setLevel(logging.DEBUG)

DEBUG = True

# Gemini AI import (with fallback)
try:
    import google.generativeai as genai
except ImportError:
    genai = None

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    os.environ["GOOGLE_API_KEY"] = GEMINI_API_KEY

bot_token = os.getenv("BOT_TOKEN")

if not bot_token:
    print("Error: BOT_TOKEN not found in .env file. Please make sure it is set.")
    sys.exit(1)

bot = Client(token=bot_token)

# Add New World funny statuses and details (from appid.py)
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
    {"name": "Open World PvP", "state": "Von 5er-Gruppe 'gefairplayt'."},
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

NW_EXTRA_DETAILS = [
    "Level 60 • Großaxt-Meister",
    "Territorium: Immerfall",
    "Company: Die Verlorenen",
    "Wassermark: 625",
    "Gold: 3.50 (arm aber sexy)",
    "Azoth: 0 (klassisch)",
    "Reparatur-Teile: ∞ (brauch ich)",
    "Handwerk: Waffenschmied 200",
    "Trading Post Sniper",
    "Expeditionen gecleart: 247",
    "PvP K/D: 0.3 (stolz drauf)",
    "Stunden gespielt: Zu viele",
    "Lieblings-Gebiet: Weavers Fen",
    "Hasst: Dynastien-Schiffbruch",
    "Status: Überlebt... knapp"
]

if Observer and FileSystemEventHandler:

    class CodeChangeHandler(FileSystemEventHandler):
        def __init__(self, bot):
            self.bot = bot
            super().__init__()

        def on_modified(self, event):
            if event.is_directory:
                return
            # Ensure src_path is a string and endswith uses a tuple of str
            if isinstance(event.src_path, str) and event.src_path.endswith(tuple([".py"])):
                print(f"Code change detected in {event.src_path}. Reloading...")
                asyncio.create_task(self.reload_bot())

        async def reload_bot(self):
            for extension in list(bot.ext):
                try:
                    bot.unload_extension(extension)
                    print(f"Unloaded extension: {extension}")
                except Exception as e:
                    print(f"Failed to unload extension {extension}: {e}")

            extensions_dir = os.path.dirname(os.path.abspath(__file__))
            for filename in os.listdir(extensions_dir):
                if filename.endswith(".py") and filename != "main.py":
                    extension = filename[:-3]
                    try:
                        bot.load_extension(extension)
                        print(f"Loaded extension: {extension}")
                    except Exception as e:
                        print(f"Failed to load extension {extension}: {e}")
else:
    print("Watchdog is not available. Code reloading will not work.")

    class CodeChangeHandler:
        pass


@listen()
async def on_startup():
    print(f"Logged in as {bot.user}")


async def rotate_funny_presence(bot, interval=60):
    await bot.wait_until_ready()
    while True:
        status = random.choice(NW_FUNNY_STATUSES)
        detail = random.choice(NW_EXTRA_DETAILS)
        funny_status = f"{status['name']} – {status['state']} | {detail}"
        await bot.change_presence(
            status=interactions.Status.ONLINE,
            activity=interactions.Activity(
                name=funny_status,
                type=interactions.ActivityType.GAME
            )
        )
        await asyncio.sleep(interval)


@bot.event()
async def on_ready():
    print("I am ready!")
    logging.info(f"Bot is connected as {bot.user.username} (ID: {bot.user.id})")
    # Start rotating funny New World statuses in the background
    asyncio.create_task(rotate_funny_presence(bot, interval=60))


@slash_command("ping")
async def ping(ctx):
    action_rows = [
        interactions.ActionRow(
            interactions.Button(
                style=interactions.ButtonStyle.DANGER,
                label="Danger Button",
            )
        )
    ]

    embed = interactions.Embed(title="Pong!", description="Pong!", color=BrandColours.BLURPLE)
    for i in range(5):
        embed.add_field(name=f"Field {i}", value=f"Value {uuid.uuid4()}")

    if DEBUG:
        embed.add_field(name="Debug Info", value=f"Python: {sys.version}\nJurigged: Active\nTime: {uuid.uuid4()}")

    await ctx.send("Pong!", components=action_rows, embeds=embed)


@slash_command("components")
async def components(ctx):
    selects = [
        [interactions.ChannelSelectMenu()],
        [interactions.RoleSelectMenu()],
        [interactions.UserSelectMenu()],
        [interactions.MentionableSelectMenu()],
        [interactions.StringSelectMenu("test", "test 2", "test 3")],
    ]
    await ctx.send("Select menus", components=selects)
    await ctx.send(
        "Buttons",
        components=[interactions.Button(label="test", style=ButtonStyle.PRIMARY)],
    )


@slash_command("help", description="Show all available commands and their descriptions")
@slash_option("command", "Get detailed help for a specific command", opt_type=interactions.OptionType.STRING, required=False)
async def help_command(ctx: interactions.SlashContext, command: Optional[str] = None):
    if command:
        command = command.lower().strip()
        command_details = {
            "nwdb": {
                "title": "🎮 New World Database Lookup",
                "description": "Look up items from New World Database",
                "usage": "/nwdb [item_name]",
                "parameters": [
                    {"name": "item_name", "description": "The name of the item to look up (with autocomplete)"}
                ],
                "examples": ["/nwdb iron ingot", "/nwdb orichalcum"],
                "notes": "• Shows detailed item information\n• Includes crafting recipes when available\n• Calculate button lets you determine resources needed for multiple crafts"
            },
            "calculator": {
                "title": "🧮 Calculator",
                "description": "Perform mathematical calculations with support for various functions",
                "usage": "/calculator [expression]",
                "parameters": [
                    {"name": "expression", "description": "The mathematical expression to calculate"}
                ],
                "notes": "• Supports basic operations: +, -, *, /, ^\n• Functions: sin, cos, tan, asin, acos, atan, sqrt, cbrt\nlog, log10, log2, abs, round, floor, ceil, trunc\n• Constants: pi, e"
            },
            "ask": {
                "title": "🤖 Ask Gemini AI",
                "description": "Ask questions to Google's Gemini AI model",
                "usage": "/ask [prompt]",
                "parameters": [
                    {"name": "prompt", "description": "Your question for Gemini AI"}
                ],
                "examples": ["/ask What is the capital of France?", "/ask Explain quantum computing"],
                "notes": "• Powered by Google's Gemini 2.0 Flash model\n• Responses may be truncated if they exceed Discord's character limit"
            },
            "ping": {
                "title": "📡 Ping",
                "description": "Check if the bot is online and responsive",
                "usage": "/ping",
                "parameters": [],
                "examples": ["/ping"],
                "notes": "• Shows debug information when debug mode is enabled"
            },
            "debug": {
                "title": "⚙️ Debug",
                "description": "Toggle debug mode or check debug status",
                "usage": "/debug [mode]",
                "parameters": [
                    {"name": "mode", "description": "Turn debug mode on or off (optional)"}
                ],
                "examples": ["/debug", "/debug on", "/debug off"],
                "notes": "• Shows Python version and loaded extensions\n• Debug mode enables additional logging"
            },
            "record": {
                "title": "🎙️ Record",
                "description": "Record audio in your voice channel",
                "usage": "/record [duration]",
                "parameters": [
                    {"name": "duration", "description": "The duration of the recording in seconds"}
                ],
                "examples": ["/record 30"],
                "notes": "• You must be in a voice channel to use this command\n• Recordings are saved as MP3 files"
            },
            "petpet": {
                "title": "🐾 Petpet",
                "description": "Generate a petpet GIF for a user",
                "usage": "/petpet @user",
                "parameters": [
                    {"name": "user", "description": "The user to pet"}
                ],
                "examples": ["/petpet @Inas"],
                "notes": "• Generates a fun animated petpet GIF for the mentioned user"
            },
            "randomgif": {
                "title": "🎲 Random GIF",
                "description": "Send a random GIF from Tenor",
                "usage": "/randomgif",
                "parameters": [],
                "examples": ["/randomgif"],
                "notes": "• Returns a random trending/fun GIF from Tenor"
            }
        }

        if command in command_details:
            details = command_details[command]
            embed = interactions.Embed(
                title=details["title"],
                description=details["description"],
                color=BrandColours.BLURPLE
            )
            embed.add_field(name="Usage", value=f"```{details['usage']}```", inline=False)
            if details["parameters"]:
                param_str = "\n".join([f"**{p['name']}**: {p['description']}" for p in details["parameters"]])
                embed.add_field(name="Parameters", value=param_str, inline=False)
            if details.get("examples"):
                example_str = "\n".join(details["examples"])
                embed.add_field(name="Examples", value=example_str, inline=False)
            if details.get("notes"):
                embed.add_field(name="Notes", value=details["notes"], inline=False)
            await ctx.send(embeds=embed)
            return
        else:
            await ctx.send(f"No detailed help available for command: `{command}`\nUse `/help` to see all available commands.", ephemeral=True)
            return

    help_embed = interactions.Embed(
        title="📚 Bot Commands",
        description="Here are all the available commands you can use:",
        color=BrandColours.BLURPLE
    )
    help_embed.add_field(
        name="🎮 Game Commands",
        value="**/nwdb** `item_name` - Look up an item from New World Database\n"
              "→ Shows item details and crafting recipes",
        inline=False
    )
    help_embed.add_field(
        name="🔧 Utility Commands",
        value="**/calculator** `expression` - Perform mathematical calculations\n"
              "**/ask** `prompt` - Ask Gemini AI a question\n"
              "**/ping** - Check if the bot is online\n"
              "**/help** - Show this help message",
        inline=False
    )
    help_embed.add_field(
        name="🎉 Fun Commands",
        value="**/petpet** `@user` - Generate a petpet GIF for a user\n"
              "**/randomgif** - Get a random GIF from Tenor",
        inline=False
    )
    help_embed.add_field(
        name="⚙️ Advanced Commands",
        value="**/debug** `mode` - Toggle debug mode or check status\n"
              "**/record** `duration` - Record audio in your voice channel\n"
              "**/components** - Show UI component examples",
        inline=False
    )
    help_embed.set_footer(text="Use /help <command> for more details on a specific command")
    await ctx.send(embeds=help_embed)


@slash_command("debug", description="Toggle debug mode or check debug status")
@slash_option("mode", "Turn debug mode on or off", opt_type=interactions.OptionType.STRING, required=False, choices=[
    {"name": "On", "value": "on"},
    {"name": "Off", "value": "off"}
])
async def debug_command(ctx: interactions.SlashContext, mode: Optional[str] = None):
    global DEBUG
    if mode:
        if mode.lower() == "on":
            DEBUG = True
            await ctx.send("Debug mode enabled", ephemeral=True)
        elif mode.lower() == "off":
            DEBUG = False
            await ctx.send("Debug mode disabled", ephemeral=True)
    else:
        embed = interactions.Embed(
            title="Debug Information",
            description=f"Debug Mode: {'Enabled' if DEBUG else 'Disabled'}",
            color=BrandColours.BLURPLE
        )
        embed.add_field(name="Python Version", value=sys.version.split()[0])
        embed.add_field(name="Jurigged Status", value="Active" if "jurigged" in sys.modules else "Inactive")
        embed.add_field(name="Loaded Extensions", value=", ".join(bot.ext.keys()) if bot.ext else "None")
        await ctx.send(embeds=embed, ephemeral=True)


@slash_command("record", description="Record audio in your voice channel")
@slash_option("duration", "The duration of the recording", opt_type=interactions.OptionType.NUMBER, required=True)
async def record(ctx: interactions.SlashContext, duration: int) -> None:
    try:
        if not hasattr(ctx, 'guild') or ctx.guild is None:
            await ctx.send("This command can only be used in a server.")
            return
        voice_state = getattr(ctx.guild, 'get_voice_state', lambda x: None)(ctx.author.id)
        if not voice_state or not getattr(voice_state, 'channel', None):
            await ctx.send("You must be in a voice channel to use this command.")
            return

        voice_channel = voice_state.channel
        voice_state = await voice_channel.connect()

        recorder = await voice_state.start_recording()
        await ctx.send(f"Recording for {duration} seconds")
        await asyncio.sleep(duration)
        await voice_state.stop_recording()

        await ctx.send(
            "Here is your recording", files=[File(f, file_name=f"{user_id}.mp3") for user_id, f in recorder.output.items()]
        )
    except Exception as e:
        logging.exception(f"Error in record command: {e}")
        await ctx.send(f"An error occurred while recording: {e}")


@slash_command("modal")
async def modal(ctx):
    _modal = interactions.Modal(
        interactions.ShortText(
            label="Number of Crafts",
            placeholder="Placeholder",
            required=True,
            min_length=5,
            max_length=10,
        ),
        interactions.ParagraphText(
            label="Paragraph Text",
            placeholder="Placeholder",
            required=True,
            min_length=5,
            max_length=10,
        ),
        title="Modal",
    )
    await ctx.send_modal(_modal)


@listen()
async def on_component(event: interactions.events.Component):
    ctx: interactions.ComponentContext = event.ctx

    if ctx.custom_id.startswith("calculate_crafts:"):
        item_name = ctx.custom_id.split(":")[1]
        modal_id = f"craft_modal:{item_name}"
        craft_modal = interactions.Modal(
            interactions.ShortText(
                label="Number of Crafts",
                placeholder="Enter the number of crafts",
                custom_id=f"num_crafts:{item_name}",
                required=True,
                min_length=5,
                max_length=10
            ),
            title=f"Calculate Crafts for {item_name}",
            custom_id=modal_id
        )
        await ctx.send_modal(craft_modal)
    elif ctx.custom_id.startswith("calc_copy:"):
        result = ctx.custom_id.split(":", 1)[1]
        await ctx.send(f"```{result}```", ephemeral=True)
    elif ctx.custom_id == "calc_help":
        help_embed = interactions.Embed(
            title="📊 Calculator Help",
            description="Here are the available functions and operations you can use:",
            color=BrandColours.BLURPLE
        )

        help_embed.add_field(
            name="Basic Operations",
            value="+ (addition)\n- (subtraction)\n* (multiplication)\n/ (division)\n^ or ** (exponentiation)",
            inline=True
        )

        help_embed.add_field(
            name="Constants",
            value="pi (π = 3.14159...)\ne (Euler's number = 2.71828...)",
            inline=True
        )

        help_embed.add_field(
            name="Functions",
            value="sin, cos, tan\nasin, acos, atan\nsqrt, cbrt\nlog, log10, log2\nabs, round\nfloor, ceil, trunc",
            inline=True
        )

        await ctx.send(embeds=help_embed, ephemeral=True)
        item_name = ctx.custom_id.split(":")[1]
        modal_id = f"craft_modal:{item_name}"
        craft_modal = interactions.Modal(
            interactions.ShortText(
                label="Number of Crafts",
                placeholder="Enter the number of crafts",
                custom_id=f"num_crafts:{item_name}",
                required=True,
                min_length=5,
                max_length=10
            ),
            title=f"Calculate Crafts for {item_name}",
            custom_id=modal_id
        )
        await ctx.send_modal(craft_modal)


@listen()
async def on_modal(event):
    ctx: ModalContext = event.ctx

    if DEBUG:
        logging.info(f"Modal responses: {ctx.responses}")
        logging.info(f"Modal custom_id: {ctx.custom_id}")

    if "craft_modal:" in ctx.custom_id:
        try:
            item_name = ctx.custom_id.split(":")[1]
        except IndexError:
            await ctx.send("Could not determine item name.", ephemeral=True)
            return

        try:
            num_crafts_str = list(ctx.responses.values())[0]
        except (IndexError, AttributeError):
            await ctx.send("Could not get number of crafts from the form.", ephemeral=True)
            return

        try:
            num_crafts = int(num_crafts_str)
            if num_crafts <= 0:
                await ctx.send("Please enter a positive number.", ephemeral=True)
                return
        except ValueError:
            await ctx.send("Please enter a valid number.", ephemeral=True)
            return

        item_data = items.load_items_from_csv('items.csv')
        if not item_data:
            await ctx.send("Could not load item data.", ephemeral=True)
            return

        item_name_lower = item_name.lower()

        if item_name_lower not in item_data:
            await ctx.send(f"Item '{item_name}' not found in the database.", ephemeral=True)
            return

        item = item_data[item_name_lower]

        logging.info(f"Loaded item: {item}")

        try:
            # --- Build rich embed for item info or recipe ---
            # Use case-insensitive keys for all lookups
            def get_key(keys):
                for k in item.keys():
                    if k.lower() in [key.lower() for key in keys]:
                        return k
                return None

            # Title
            title = item.get(get_key(['Name', 'name', 'Item Name']), 'Unknown Item')
            description = item.get(get_key(['Description', 'description', 'Flavor Text']), '')
            icon_url = item.get(get_key(['Icon', 'icon', 'Icon Path', 'icon_url']), '')
            tier = item.get(get_key(['Tier', 'tier']), '')
            rarity = item.get(get_key(['Rarity', 'rarity']), '')
            gear_score = item.get(get_key(['Gear Score', 'base_gear_score', 'Base Gear Score']), '')
            weight = item.get(get_key(['Weight', 'weight']), '')
            durability = item.get(get_key(['Durability', 'durability']), '')
            max_stack = item.get(get_key(['Max Stack Size', 'max_stack', 'Max Stack']), '')
            item_type = item.get(get_key(['Item Type', 'resource_type', 'Type']), '')
            perks = item.get(get_key(['Perks', 'perks']), '')

            embed = interactions.Embed(
                title=title,
                description=description,
                color=BrandColours.GREEN if item_type else BrandColours.BLURPLE
            )

            # Main Info Section
            info_lines = []
            if gear_score:
                info_lines.append(f"**Gear Score:** {gear_score}")
            if weight:
                info_lines.append(f"**Weight:** {weight}")
            if durability:
                info_lines.append(f"**Durability:** {durability}")
            if max_stack:
                info_lines.append(f"**Max Stack:** {max_stack}")
            if tier:
                info_lines.append(f"**Tier:** {tier}")
            if rarity:
                info_lines.append(f"**Rarity:** {rarity}")
            if item_type:
                info_lines.append(f"**Type:** {item_type}")
            if info_lines:
                embed.add_field(name="Info", value="\n".join(info_lines), inline=False)

            # Perks (try to split and add icons/images like nwdb.info)
            if perks:
                perk_lines = []
                for perk in str(perks).split(","):
                    perk = perk.strip()
                    # Try to pretty-print known perks (replace IDs with readable names)
                    pretty = perk
                    if perk.startswith('PerkID_'):
                        pretty = perk.replace('PerkID_', '').replace('_', ' ').title()
                    # Map perk keywords to NWDB-style unicode or emoji icons
                    if 'gem' in perk.lower() or 'socket' in perk.lower():
                        icon = '💠'
                    elif 'random' in perk.lower():
                        icon = '🎲'
                    elif 'awareness' in perk.lower():
                        icon = '🧠'
                    elif 'hearty' in perk.lower():
                        icon = '💚'
                    elif 'affinity' in perk.lower():
                        icon = '✨'
                    elif 'magnify' in perk.lower():
                        icon = '🔆'
                    elif 'sentry' in perk.lower():
                        icon = '🛡️'
                    elif 'refreshing' in perk.lower():
                        icon = '💧'
                    elif 'enchanted' in perk.lower():
                        icon = '🪄'
                    elif 'foundation' in perk.lower():
                        icon = '🏗️'
                    elif 'ward' in perk.lower():
                        icon = '🛡️'
                    elif 'cooldown' in perk.lower():
                        icon = '⏱️'
                    elif 'stamina' in perk.lower():
                        icon = '⚡'
                    elif 'attribute' in perk.lower():
                        icon = '🔹'
                    else:
                        icon = '•'
                    perk_lines.append(f"{icon} {pretty}")
                embed.add_field(name="Perks", value="\n".join(perk_lines), inline=False)

            # Add main item icon (top left)
            # Try to use Hi Res Icon Path, Icon Path, or icon_url (in that order)
            icon_url = (
                item.get(get_key(['Hi Res Icon Path', 'hi_res_icon_path']), '') or
                item.get(get_key(['Icon Path', 'icon_path', 'Icon']), '') or
                item.get(get_key(['icon_url', 'Icon_Url']), '')
            )
            if icon_url:
                embed.set_thumbnail(url=icon_url)

            # Add big gear score icon if available
            if gear_score:
                # Use a custom emoji or Unicode for the gear score icon
                embed.add_field(name="\u200b", value=f"<:nwdb_gear:> **{gear_score}**", inline=False)

            # Add more fields for stats if available (e.g., Armor Rating, etc.)
            armor_rating_elem = item.get(get_key(['Armor Rating - Elemental', 'armor_rating_elemental']), '')
            armor_rating_phys = item.get(get_key(['Armor Rating - Physical', 'armor_rating_physical']), '')
            if armor_rating_elem or armor_rating_phys:
                stats = []
                if armor_rating_elem:
                    stats.append(f"{armor_rating_elem} Armor Rating - Elemental")
                if armor_rating_phys:
                    stats.append(f"{armor_rating_phys} Armor Rating - Physical")
                embed.add_field(name="Stats", value="\n".join(stats), inline=False)

            # Add flavor text/description in italics if available
            if description:
                embed.add_field(name="\u200b", value=f"*{description}*", inline=False)

            await ctx.send(embeds=embed)
        except Exception as e:
            logging.exception(f"Error in nwdb command: {e}")
            await ctx.send("An error occurred while processing your request.", ephemeral=True)


@slash_command(name="nwdb", description="Look up items from New World Database")
@slash_option(name="item_name", description="The name of the item to look up", opt_type=interactions.OptionType.STRING, required=True, autocomplete=True)
async def nwdb(ctx: interactions.SlashContext, item_name: str):
    try:
        item_data = items.load_items_from_csv('items.csv')
        if not item_data:
            await ctx.send("No item data found. Please contact the server administrator.", ephemeral=True)
            return

        item_name_lower = item_name.lower()
        if item_name_lower not in item_data:
            await ctx.send(f"Item '{item_name}' not found in the database.", ephemeral=True)
            return

        item = item_data[item_name_lower]

        logging.info(f"Loaded item: {item}")

        try:
            # --- Build rich embed for item info or recipe ---
            # Use case-insensitive keys for all lookups
            def get_key(keys):
                for k in item.keys():
                    if k.lower() in [key.lower() for key in keys]:
                        return k
                return None

            # Title
            title = item.get(get_key(['Name', 'name', 'Item Name']), 'Unknown Item')
            description = item.get(get_key(['Description', 'description', 'Flavor Text']), '')
            icon_url = item.get(get_key(['Icon', 'icon', 'Icon Path', 'icon_url']), '')
            tier = item.get(get_key(['Tier', 'tier']), '')
            rarity = item.get(get_key(['Rarity', 'rarity']), '')
            gear_score = item.get(get_key(['Gear Score', 'base_gear_score', 'Base Gear Score']), '')
            weight = item.get(get_key(['Weight', 'weight']), '')
            durability = item.get(get_key(['Durability', 'durability']), '')
            max_stack = item.get(get_key(['Max Stack Size', 'max_stack', 'Max Stack']), '')
            item_type = item.get(get_key(['Item Type', 'resource_type', 'Type']), '')
            perks = item.get(get_key(['Perks', 'perks']), '')

            embed = interactions.Embed(
                title=title,
                description=description,
                color=BrandColours.GREEN if item_type else BrandColours.BLURPLE
            )

            # Main Info Section
            info_lines = []
            if gear_score:
                info_lines.append(f"**Gear Score:** {gear_score}")
            if weight:
                info_lines.append(f"**Weight:** {weight}")
            if durability:
                info_lines.append(f"**Durability:** {durability}")
            if max_stack:
                info_lines.append(f"**Max Stack:** {max_stack}")
            if tier:
                info_lines.append(f"**Tier:** {tier}")
            if rarity:
                info_lines.append(f"**Rarity:** {rarity}")
            if item_type:
                info_lines.append(f"**Type:** {item_type}")
            if info_lines:
                embed.add_field(name="Info", value="\n".join(info_lines), inline=False)

            # Perks (try to split and add icons/images like nwdb.info)
            if perks:
                perk_lines = []
                for perk in str(perks).split(","):
                    perk = perk.strip()
                    # Try to pretty-print known perks (replace IDs with readable names)
                    pretty = perk
                    if perk.startswith('PerkID_'):
                        pretty = perk.replace('PerkID_', '').replace('_', ' ').title()
                    # Map perk keywords to NWDB-style unicode or emoji icons
                    if 'gem' in perk.lower() or 'socket' in perk.lower():
                        icon = '💠'
                    elif 'random' in perk.lower():
                        icon = '🎲'
                    elif 'awareness' in perk.lower():
                        icon = '🧠'
                    elif 'hearty' in perk.lower():
                        icon = '💚'
                    elif 'affinity' in perk.lower():
                        icon = '✨'
                    elif 'magnify' in perk.lower():
                        icon = '🔆'
                    elif 'sentry' in perk.lower():
                        icon = '🛡️'
                    elif 'refreshing' in perk.lower():
                        icon = '💧'
                    elif 'enchanted' in perk.lower():
                        icon = '🪄'
                    elif 'foundation' in perk.lower():
                        icon = '🏗️'
                    elif 'ward' in perk.lower():
                        icon = '🛡️'
                    elif 'cooldown' in perk.lower():
                        icon = '⏱️'
                    elif 'stamina' in perk.lower():
                        icon = '⚡'
                    elif 'attribute' in perk.lower():
                        icon = '🔹'
                    else:
                        icon = '•'
                    perk_lines.append(f"{icon} {pretty}")
                embed.add_field(name="Perks", value="\n".join(perk_lines), inline=False)

            # Add main item icon (top left)
            # Try to use Hi Res Icon Path, Icon Path, or icon_url (in that order)
            icon_url = (
                item.get(get_key(['Hi Res Icon Path', 'hi_res_icon_path']), '') or
                item.get(get_key(['Icon Path', 'icon_path', 'Icon']), '') or
                item.get(get_key(['icon_url', 'Icon_Url']), '')
            )
            if icon_url:
                embed.set_thumbnail(url=icon_url)

            # Add big gear score icon if available
            if gear_score:
                # Use a custom emoji or Unicode for the gear score icon
                embed.add_field(name="\u200b", value=f"<:nwdb_gear:> **{gear_score}**", inline=False)

            # Add more fields for stats if available (e.g., Armor Rating, etc.)
            armor_rating_elem = item.get(get_key(['Armor Rating - Elemental', 'armor_rating_elemental']), '')
            armor_rating_phys = item.get(get_key(['Armor Rating - Physical', 'armor_rating_physical']), '')
            if armor_rating_elem or armor_rating_phys:
                stats = []
                if armor_rating_elem:
                    stats.append(f"{armor_rating_elem} Armor Rating - Elemental")
                if armor_rating_phys:
                    stats.append(f"{armor_rating_phys} Armor Rating - Physical")
                embed.add_field(name="Stats", value="\n".join(stats), inline=False)

            # Add flavor text/description in italics if available
            if description:
                embed.add_field(name="\u200b", value=f"*{description}*", inline=False)

            await ctx.send(embeds=embed)
        except Exception as e:
            logging.exception(f"Error in nwdb command: {e}")
            await ctx.send("An error occurred while processing your request.", ephemeral=True)
    except Exception as e:
        logging.exception(f"Error in nwdb command: {e}")
        await ctx.send("An error occurred while processing your request.", ephemeral=True)


@nwdb.autocomplete("item_name")
async def nwdb_autocomplete(ctx: interactions.AutocompleteContext):
    try:
        if not ctx.input_text:
            return []

        search_term = ctx.input_text.lower().strip()
        choices = []

        try:
            item_data = items.load_items_from_csv('items.csv')
            if not item_data:
                return []
            
            # Collect matching items
            for item in item_data.values():
                if len(choices) >= 25:  # Discord's limit
                    break

                try:
                    item_name_column = next((col for col in item.keys() if col.lower() == 'name'), None)
                    if not item_name_column:
                        item_name_column = next((col for col in item.keys() if col.lower() in ['item_name', 'itemname']), None)
                    
                    if item_name_column and item[item_name_column]:
                        item_name = str(item[item_name_column])
                        if item_name.lower().startswith(search_term):
                            truncated = truncate_discord_choice(item_name)
                            utf16_len = len(truncated.encode('utf-16-le')) // 2
                            if DEBUG:
                                logging.info(f"Autocomplete candidate: '{truncated}' | len={len(truncated)} | utf16={utf16_len} | bytes={truncated.encode('utf-8')}")
                            if truncated and utf16_len <= 25 and len(truncated) <= 25:
                                choices.append({"name": truncated, "value": truncated})
                            elif DEBUG:
                                logging.error(f"Rejected autocomplete value: '{truncated}' (len={len(truncated)}, utf16={utf16_len}, bytes={truncated.encode('utf-8')})")

                except Exception:
                    continue

            # Final check: ensure all names and values are strings and log the return value
            if DEBUG:
                logging.info(f"Sending autocomplete choices: {choices}")
            await ctx.send(choices=choices)
            # Do not return anything here
        except Exception as e:
            if DEBUG:
                logging.error(f"Error processing items: {e}")
            return []

    except Exception as e:
        logging.error(f"Error in autocomplete: {e}")
        return []


def truncate_discord_choice(s, max_codeunits=25):
    s = unicodedata.normalize('NFC', s)
    s = re.sub(r'[^\x20-\x7E\u00A0-\uFFFF]', '', s)  # keep only printable unicode
    s = s.replace('\n', ' ').replace('\r', ' ').strip()
    s = re.sub(r' +', ' ', s)
    encoded = s.encode('utf-16-le')
    if len(encoded) <= max_codeunits * 2:
        return s
    truncated = encoded[:max_codeunits * 2]
    if len(truncated) % 2 != 0:
        truncated = truncated[:-1]
    return truncated.decode('utf-16-le', errors='ignore').strip()


# Update jurigged import with proper encoding
try:
    import codecs
    codecs.register_error('strict', codecs.replace_errors)
    bot.load_extension("interactions.ext.jurigged")
    print("Live code reloading enabled with jurigged")
except ImportError:
    print("Jurigged not available. Install with: pip install jurigged")
except Exception as e:
    print(f"Failed to load jurigged extension: {e}")

@slash_command("ask", description="Ask Gemini AI a question")
@slash_option("prompt", "Your question for Gemini AI", opt_type=interactions.OptionType.STRING, required=True)
async def ask_command(ctx: interactions.SlashContext, prompt: str):
    from os import getenv
    GEMINI_API_KEY = getenv("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        await ctx.send("Gemini API key is not set. Please contact the administrator.", ephemeral=True)
        return
    if genai is None:
        await ctx.send("Gemini API is not installed. Please run 'pip install google-generativeai' and restart the bot.", ephemeral=True)
        return
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model_name = "models/gemini-1.5-flash-latest"
        model = genai.GenerativeModel(model_name)
        try:
            response = model.generate_content(prompt)
        except Exception as e:
            if "404" in str(e) or "not found" in str(e).lower():
                await ctx.send(
                    "The Gemini Flash model is not available or not supported for content generation. Please check your API key and model access, or contact the administrator.",
                    ephemeral=True
                )
                return
            raise
        text = response.text.strip() if hasattr(response, 'text') else str(response)
        if len(text) > 1900:
            text = text[:1900] + "... (truncated)"
        await ctx.send(text)
    except Exception as e:
        logging.exception(f"Error in /ask command: {e}")
        await ctx.send(f"An error occurred while processing your request: {e}", ephemeral=True)

@slash_command("petpet", description="Generate a petpet GIF for a user")
@slash_option(
    "user",
    "The user to pet",
    opt_type=interactions.OptionType.USER,
    required=True,
)
async def petpet(ctx: interactions.SlashContext, user: interactions.User):
    try:
        avatar_url = user.avatar_url
        if avatar_url and not avatar_url.endswith(".png"):
            avatar_url = avatar_url.split("?")[0] + ".png"
        api_url = f"https://some-random-api.ml/canvas/petpet?avatar={avatar_url}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, timeout=10) as resp:
                    if resp.status == 200:
                        gif_bytes = await resp.read()
                        file = File(gif_bytes, file_name="petpet.gif")
                        await ctx.send(f"Here's a petpet for {user.mention}!", files=[file])
                    else:
                        # If the API is up but returns an error, show the error
                        try:
                            error_json = await resp.json()
                            error_msg = error_json.get("error") or error_json.get("message") or "API error"
                        except Exception:
                            error_msg = "API error"
                        await ctx.send(f"Failed to generate petpet GIF: {error_msg}", ephemeral=True)
        except (aiohttp.ClientConnectorError, aiohttp.ClientOSError):
            await ctx.send("The petpet API is currently unreachable. Please try again later. (DNS or network error)", ephemeral=True)
        except asyncio.TimeoutError:
            await ctx.send("The petpet API took too long to respond. Please try again later.", ephemeral=True)
        except Exception as e:
            logging.error(f"Error connecting to petpet API: {e}")
            await ctx.send("A network error occurred while generating the petpet GIF. Please try again later.", ephemeral=True)
    except Exception as e:
        logging.error(f"Error in /petpet command: {e}")
        await ctx.send(f"An error occurred while generating the petpet GIF: {e}", ephemeral=True)

@slash_command("randomgif", description="Send a random GIF from Tenor")
async def randomgif(ctx: interactions.SlashContext):
    TENOR_API_KEY = os.getenv("TENOR_API_KEY")
    if not TENOR_API_KEY:
        await ctx.send("Tenor API key is not set. Please set TENOR_API_KEY in your .env file.", ephemeral=True)
        return
    try:
        async with aiohttp.ClientSession() as session:
            # You can change the search term for more variety
            search_term = random.choice(["funny", "meme", "cat", "dog", "gaming", "reaction", "random"])
            url = f"https://tenor.googleapis.com/v2/search?q={search_term}&key={TENOR_API_KEY}&limit=20&media_filter=gif"
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    results = data.get("results", [])
                    if not results:
                        await ctx.send("No GIFs found.", ephemeral=True)
                        return
                    gif = random.choice(results)
                    gif_url = gif["media_formats"]["gif"]["url"]
                    await ctx.send(gif_url)
                else:
                    await ctx.send("Failed to fetch GIF from Tenor.", ephemeral=True)
    except Exception as e:
        logging.error(f"Error in /randomgif command: {e}")
        await ctx.send("An error occurred while fetching a GIF.", ephemeral=True)

try:
    bot.start(bot_token)
except Exception as e:
    logging.error(f"Failed to start the bot: {e}")


@bot.event()
async def on_disconnect():
    logging.warning("Bot disconnected. Attempting to reconnect...")
    # Implement a reconnection strategy here, e.g., wait and then restart the bot
    await asyncio.sleep(5)  # Wait for 5 seconds before attempting to reconnect
    logging.info("Attempting to reconnect...")
    try:
        bot.start(bot_token)  # Restart the bot (not awaited)
    except Exception as e:
        logging.error(f"Failed to reconnect: {e}")


@bot.event()
async def on_message_create(event):
    # Try to get the message object from different possible attributes
    message = getattr(event, "message", None) or getattr(event, "data", None)
    if not message:
        return

    # Defensive: author may be a dict or object
    author = getattr(message, "author", None)
    if not author:
        author = getattr(message, "user", None)
    if not author:
        # Try dict fallback
        author = message.get("author") if isinstance(message, dict) else None
    if not author:
        return
    # Check if author is a bot
    is_bot = getattr(author, "bot", None)
    if is_bot is None and isinstance(author, dict):
        is_bot = author.get("bot", False)
    if is_bot:
        return

    # Try both .me and .user for the bot's user object
    bot_self = getattr(bot, "me", None) or getattr(bot, "user", None)
    if not bot_self or not hasattr(bot_self, "id"):
        return
    bot_id = str(getattr(bot_self, "id", None))

    # Mentions may be a list of objects or dicts
    mentions = getattr(message, "mentions", []) or []
    if not mentions and isinstance(message, dict):
        mentions = message.get("mentions", [])
    mentioned_ids = set()
    for m in mentions:
        mid = getattr(m, "id", None)
        if mid is None and isinstance(m, dict):
            mid = m.get("id")
        if mid:
            mentioned_ids.add(str(mid))

    # Also check if the bot was mentioned by raw mention string in content
    content = getattr(message, "content", "") or getattr(message, "text", "")
    # Add debug logging to see if the mention is detected
    logging.debug(f"Message content: {content}")
    logging.debug(f"Mentions: {mentioned_ids}, Bot ID: {bot_id}")
    if not mentioned_ids and bot_id and f"<@{bot_id}>" in content:
        mentioned_ids.add(bot_id)

    # Add debug log to confirm mention detection
    if bot_id in mentioned_ids:
        logging.info(f"Bot was mentioned in message: {content}")
        prompt = (
            "You are a funny New World MMO Discord bot. "
            "Someone just pinged you in chat. Respond with a witty, playful, and New World-themed message, "
            "as if you are a quirky NPC or player in Aeternum. Keep it short and fun."
        )
        user_message = content
        full_prompt = f"{prompt}\nUser said: {user_message}\nBot reply:"

        if genai is None or not GEMINI_API_KEY:
            reply = "Ich bin zu beschäftigt mit Truthahn-Jagd, um zu antworten! (Gemini AI nicht verfügbar)"
        else:
            try:
                genai.configure(api_key=GEMINI_API_KEY)
                model = genai.GenerativeModel("models/gemini-1.5-flash-latest")
                loop = asyncio.get_running_loop()
                response = await loop.run_in_executor(None, model.generate_content, full_prompt)
                reply = response.text.strip() if hasattr(response, "text") else str(response)
                if len(reply) > 1900:
                    reply = reply[:1900] + "... (truncated)"
            except Exception as e:
                logging.exception(f"Error in mention Gemini AI reply: {e}")
                reply = "Mein Azoth ist leer, ich kann gerade nicht antworten! (AI-Fehler)"

        try:
            # Try reply, then send, then fallback to logging
            if hasattr(message, "reply") and callable(getattr(message, "reply", None)):
                await message.reply(reply, mention_author=False)
            elif hasattr(message, "channel") and callable(getattr(message.channel, "send", None)):
                await message.channel.send(reply)
            elif isinstance(message, dict) and "channel_id" in message:
                channel_id = message["channel_id"]
                try:
                    channel = await bot.fetch_channel(str(channel_id))
                    if hasattr(channel, "send") and callable(getattr(channel, "send", None)):
                        await channel.send(reply)
                    elif hasattr(channel, "send_message") and callable(getattr(channel, "send_message", None)):
                        await channel.send_message(reply)
                    else:
                        logging.warning("Fetched channel has no send/send_message method.")
                except Exception as e:
                    logging.error(f"Failed to send reply via fetched channel: {e}")
            else:
                logging.warning(f"No valid way to send reply to mention. Would have replied: {reply}")
        except Exception as e:
            logging.error(f"Failed to reply to mention: {e}")
