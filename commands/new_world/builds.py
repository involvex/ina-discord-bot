import logging
import json
import re
from typing import Optional

from interactions import ( # Added Member to imports
    Extension, slash_command, slash_option, OptionType, SlashContext, AutocompleteContext, Embed, Permissions, Client, Member
)

from settings_manager import is_bot_manager
from config import BUILDS_FILE, OWNER_ID # Added OWNER_ID to imports

logger = logging.getLogger(__name__)

class NewWorldBuilds(Extension):
    def __init__(self, bot: Client):
        self.bot = bot

    @slash_command(name="build", description="Manage saved New World builds.")
    async def build_group(self, ctx: SlashContext):
        """Base command for build management."""
        pass

    @build_group.subcommand(sub_cmd_name="add", sub_cmd_description="Add a build from nw-buddy.de.")
    @slash_option("link", "The nw-buddy.de build link", opt_type=OptionType.STRING, required=True)
    @slash_option("name", "A name for this build", opt_type=OptionType.STRING, required=True)
    async def build_add(self, ctx: SlashContext, link: str, name: str):
        if not re.match(r"^https://(www\.)?nw-buddy.de/gearsets/", link):
            await ctx.send("Please provide a valid nw-buddy.de gearset link.", ephemeral=True)
            return
        
        try:
            with open(BUILDS_FILE, 'r', encoding='utf-8') as f:
                builds = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            builds = []
        
        builds.append({"name": name, "link": link, "submitted_by": str(ctx.author.id)})
        
        with open(BUILDS_FILE, 'w', encoding="utf-8") as f:
            json.dump(builds, f, indent=2)
            
        await ctx.send(f"Build '{name}' added!", ephemeral=True)

    @build_group.subcommand(sub_cmd_name="list", sub_cmd_description="Show a list of saved builds.")
    async def build_list(self, ctx: SlashContext):
        try:
            with open(BUILDS_FILE, 'r', encoding='utf-8') as f:
                builds = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            builds = []

        if not builds:
            await ctx.send("No builds saved yet.", ephemeral=True)
            return

        embed = Embed(title="Saved Builds", color=0x3498db)
        for build in builds:
            submitter = f"<@{build.get('submitted_by', 'Unknown')}>"
            embed.add_field(name=build['name'], value=f"[Link]({build['link']}) by {submitter}", inline=False)
        
        await ctx.send(embeds=embed)

    @build_group.subcommand(sub_cmd_name="remove", sub_cmd_description="Remove a saved build.")
    @slash_option("name", "The name of the build to remove", opt_type=OptionType.STRING, required=True, autocomplete=True)
    async def build_remove(self, ctx: SlashContext, name: str):
        is_allowed = False
        if ctx.author.id == OWNER_ID: # Bot owner always has permission
            is_allowed = True
        elif is_bot_manager(int(ctx.author.id)): # Bot managers always have permission
            is_allowed = True
        elif isinstance(ctx.author, Member) and ctx.author.has_permission(Permissions.MANAGE_GUILD): # Guild managers have permission
            is_allowed = True
        
        if not is_allowed:
            await ctx.send("You do not have permission to remove builds.", ephemeral=True)
            return

        try:
            with open(BUILDS_FILE, 'r', encoding='utf-8') as f:
                builds = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            await ctx.send("No builds to remove.", ephemeral=True)
            return

        original_count = len(builds)
        builds_filtered = [b for b in builds if b.get("name", "").lower() != name.lower()]

        if len(builds_filtered) == original_count:
            await ctx.send(f"Build '{name}' not found.", ephemeral=True)
            return

        with open(BUILDS_FILE, 'w', encoding="utf-8") as f:
            json.dump(builds_filtered, f, indent=2)
        
        await ctx.send(f"Build '{name}' removed.", ephemeral=True)

    @build_remove.autocomplete("name")
    async def build_remove_autocomplete(self, ctx: AutocompleteContext):
        try:
            with open(BUILDS_FILE, 'r', encoding='utf-8') as f:
                builds = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            await ctx.send(choices=[])
            return
        
        search_term = ctx.input_text.lower()
        choices = [
            {"name": b["name"], "value": b["name"]}
            for b in builds if search_term in b.get("name", "").lower()
        ][:25]
        await ctx.send(choices=choices)

def setup(bot: Client):
    NewWorldBuilds(bot)