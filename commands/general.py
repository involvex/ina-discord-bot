import logging
import time
import math
from typing import Optional

from interactions import (
    Extension, slash_command, slash_option, OptionType, SlashContext, Embed, User, File
)

from config import (
    __version__ as config_version,
    BOT_START_TIME,
    OWNER_ID
)
from common_utils import format_uptime
from utils.image_utils import generate_petpet_gif

logger = logging.getLogger(__name__)

class GeneralCommands(Extension):
    def __init__(self, bot):
        self.bot = bot

    @slash_command("ping", description="Check if the bot is online.")
    async def ping(self, ctx: SlashContext):
        latency_ms = round(self.bot.latency * 1000)
        await ctx.send(f"Pong! Ina is online. Latency: {latency_ms}ms")

    @slash_command("help", description="Show all available commands and their descriptions")
    @slash_option("command", "Get detailed help for a specific command", opt_type=OptionType.STRING, required=False)
    async def help_command(self, ctx: SlashContext, command: Optional[str] = None):
        commands_info = {
            "ping": {"desc": "Check if the bot is online.", "usage": "/ping", "category": "General"},
            "help": {"desc": "Show available commands or help for a specific command.", "usage": "/help [command_name]", "category": "General"}, # Corrected typo
            "petpet": {"desc": "Give a New World petting ritual to a user!", "usage": "/petpet <user>", "category": "General"},
            "calculate": {"desc": "Perform a calculation with New World magic!", "usage": "/calculate <expression>", "category": "General"},
            "uptime": {"desc": "Show how long Ina has been adventuring online.", "usage": "/uptime", "category": "General"},
            "about": {"desc": "Show information about Ina's New World Bot.", "usage": "/about", "category": "General"},
            "nwdb": {"desc": "Look up items from New World Database.", "usage": "/nwdb <item_name>", "category": "New World"},
            "perk": {"desc": "Look up information about a specific New World perk.", "usage": "/perk <perk_name>", "category": "New World"},
            "recipe": {"desc": "Show the full recipe breakdown for a craftable item.", "usage": "/recipe <item_name>", "category": "New World"},
            "calculate_craft": {"desc": "Calculate resources needed to craft an item, including intermediates.", "usage": "/calculate_craft <item_name> [amount]", "category": "New World"},
            "build add": {"desc": "Add a build from nw-buddy.de.", "usage": "/build add <link> <name> [keyperks]", "category": "Builds"},
            "build list": {"desc": "Show a list of saved builds.", "usage": "/build list", "category": "Builds"},
            "build remove": {"desc": "Remove a saved build.", "usage": "/build remove <name>", "perms": "Manage Server or Bot Manager", "category": "Builds"},
            "manage update": {"desc": "Pulls updates from GitHub and restarts the bot.", "usage": "/manage update", "perms": "Bot Owner", "category": "Management"},
            "manage restart": {"desc": "Shuts down the bot for manual restart.", "usage": "/manage restart", "perms": "Bot Owner/Manager", "category": "Management"},
            "settings permit": {"desc": "Grants a user bot management permissions.", "usage": "/settings permit <user>", "perms": "Server Admin or Bot Owner", "category": "Settings"},
            "settings unpermit": {"desc": "Revokes a user's bot management permissions.", "usage": "/settings unpermit <user>", "perms": "Server Admin or Bot Owner", "category": "Settings"},
            "settings listmanagers": {"desc": "Lists users with bot management permissions.", "usage": "/settings listmanagers", "perms": "Server Admin or Bot Manager/Owner", "category": "Settings"},
            "manage debug": {"desc": "Enable or disable debug logging in the console.", "usage": "/manage debug <enable|disable>", "perms": "Bot Owner/Manager", "category": "Management"},
            "manage cleanup": {"desc": "Cleans up cached files like __pycache__.", "usage": "/manage cleanup", "perms": "Bot Owner/Manager", "category": "Management"},
            "settings welcomemessages": {"desc": "Manage welcome messages. Actions: enable, disable, status.", "usage": "/settings welcomemessages <action> [channel]", "perms": "Server Admin or Bot Manager/Owner", "category": "Settings"},
            "settings logging": {"desc": "Manage server activity logging. Actions: enable, disable, status.", "usage": "/settings logging <action> [channel]", "perms": "Server Admin or Bot Manager/Owner", "category": "Settings"}
        }

        if command:
            command_name_lookup = command.lower().strip()
            info_to_display = commands_info.get(command_name_lookup)

            if info_to_display:
                embed = Embed(title=f"Help: `{info_to_display['usage']}`", color=0x7289DA)
                embed.description = info_to_display['desc']
                if 'perms' in info_to_display:
                    embed.add_field(name="Permissions Required", value=info_to_display['perms'], inline=False)
                await ctx.send(embeds=embed)
            else:
                await ctx.send(f"Command '{command}' not found. Use `/help` to see all commands.", ephemeral=True)
        else:
            categorized_commands = {}
            for info in commands_info.values():
                category = info.get("category", "Uncategorized")
                if category not in categorized_commands:
                    categorized_commands[category] = []
                categorized_commands[category].append(f"`{info['usage']}`: {info['desc']}")

            embed = Embed(title="Ina's New World Bot Commands", color=0x5865F2)
            embed.description = "Here's a list of available commands. For more details, use `/help [command_name]`."
            
            category_order = ["General", "New World", "Builds", "Settings", "Management"]
            for category_name in category_order:
                if category_name in categorized_commands:
                    if category_name == "Management" and ctx.author.id != OWNER_ID:
                        continue
                    embed.add_field(name=f"**{category_name}**", value="\n".join(categorized_commands[category_name]), inline=False)
            
            await ctx.send(embeds=embed)

    @slash_command("petpet", description="Give a New World petting ritual to a user!")
    @slash_option("user", "The user to pet (Aeternum style)", opt_type=OptionType.USER, required=True)
    async def petpet(self, ctx: SlashContext, user: User):
        await ctx.defer()
        avatar_url = user.avatar.url if user.avatar else user.default_avatar.url
        gif_buffer = await generate_petpet_gif(str(avatar_url))
        if gif_buffer:
            await ctx.send(files=[File(file=gif_buffer, file_name="petpet.gif")])
        else:
            await ctx.send("Sorry, I couldn't create the petpet animation right now.", ephemeral=True)

    @slash_command("calculate", description="Perform a calculation with New World magic!")
    @slash_option("expression", "The mathematical expression to calculate", opt_type=OptionType.STRING, required=True)
    async def calculate(self, ctx: SlashContext, expression: str):
        try:
            allowed_names = {k: v for k, v in math.__dict__.items() if not k.startswith("_")}
            result = eval(expression, {"__builtins__": {}}, allowed_names)
            await ctx.send(f"🔮 The result of `{expression}` is `{result}`.")
        except Exception as e:
            await ctx.send(f"The arcane calculation failed: {e}", ephemeral=True)

    @slash_command(name="uptime", description="Shows how long Ina has been online.")
    async def uptime_command(self, ctx: SlashContext):
        current_time = time.time()
        uptime_seconds = current_time - BOT_START_TIME
        human_readable_uptime = format_uptime(uptime_seconds)
        await ctx.send(f"🧭 Ina has been adventuring in Aeternum for: **{human_readable_uptime}**")

    @slash_command(name="about", description="Show information about Ina's New World Bot.")
    async def about_command(self, ctx: SlashContext):
        embed = Embed(
            title="About Ina's New World Bot",
            description="Your friendly companion for all things Aeternum!",
            color=0x7289DA
        )
        embed.add_field(name="Version", value=f"`{config_version}`", inline=True)
        embed.add_field(name="Creator", value="This bot was lovingly crafted by <@157968227106947072>.", inline=True)
        embed.add_field(
            name="Credits & Data Sources",
            value="• Item and perk data often references NWDB.info.\n"
                  "• Build functionality integrates with NW-Buddy.de.",
            inline=False
        )
        embed.set_footer(text="Ina's New World Bot is a fan-made project and is not affiliated with Amazon Games.")
        await ctx.send(embeds=embed)

def setup(bot):
    GeneralCommands(bot)