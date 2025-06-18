import math
from typing import Optional
from interactions import slash_command, slash_option, OptionType, Embed
from bot_client import bot
from config import __version__, OWNER_ID

@slash_command("ping", description="Check if the bot is online.")
async def ping(ctx):
    await ctx.send("Pong! Ina is online.")

@slash_command("help", description="Show all available commands and their descriptions")
@slash_option("command", "Get detailed help for a specific command", opt_type=OptionType.STRING, required=False)
async def help_command(ctx, command: Optional[str] = None):
    # This list should ideally be dynamically generated or centrally managed
    # For now, we'll keep it static as in the original main.py
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
        "about": "Show information about Ina's New World Bot.",
        "updatebot": f"Triggers the bot's update script (Owner only: <@{OWNER_ID}>).",
        "restartbot": "Requests the bot to shut down for a manual restart (requires 'Manage Server' permission).",
        "permit": "Grants a user bot management permissions (Server Administrator only).",
        "unpermit": "Revokes a user's bot management permissions (Server Administrator only).",
        "listmanagers": "Lists users with bot management permissions (Server Administrator only)."
    }
    if command and command.lower() in commands:
        await ctx.send(f"**/{command.lower().split()[0]}**: {commands[command.lower()]}")
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

@slash_command("about", description="Show information about Ina's New World Bot.")
async def about_command(ctx):
    embed = Embed(
        title="About Ina's New World Bot",
        description="Your friendly companion for all things Aeternum!",
        color=0x7289DA
    )
    embed.add_field(name="Version", value=f"`{__version__}`", inline=True)
    embed.add_field(name="Creator", value=f"This bot was lovingly crafted by <@{OWNER_ID}>.", inline=True)
    embed.add_field(
        name="Credits & Data Sources",
        value="• Item and perk data often references NWDB.info.\n"
              "• Build functionality integrates with NW-Buddy.de.",
        inline=False
    )
    embed.set_footer(text="Ina's New World Bot is a fan-made project and is not affiliated with Amazon Games or New World.")
    await ctx.send(embeds=embed)