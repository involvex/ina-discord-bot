import logging
import os
import asyncio

from interactions import (
    Extension,
    slash_command,
    slash_option,
    OptionType,
    SlashContext,
    Permissions,
    Client,
)

from settings_manager import is_bot_manager, add_bot_manager, remove_bot_manager, set_dev_mode_setting, get_dev_mode_setting

logger = logging.getLogger(__name__)

class AdminCommands(Extension):
    def __init__(self, bot: Client):
        self.bot = bot

    @slash_command(name="manage", description="Bot management commands (Owner/Manager only).")
    async def manage_group(self, ctx: SlashContext):
        """Base command for bot management."""
        # Check for Administrator permission or bot manager role
        if not ctx.author.has_permission(Permissions.ADMINISTRATOR) and not is_bot_manager(int(ctx.author.id)):
            await ctx.send("You do not have permission to use this command.", ephemeral=True)
            return
        pass

    @manage_group.subcommand(sub_cmd_name="permit", sub_cmd_description="Grants a user bot management permissions.")
    @slash_option("user", "The user to grant permissions to", opt_type=OptionType.USER, required=True)
    async def manage_permit(self, ctx: SlashContext, user):
        if add_bot_manager(int(user.id)):
            await ctx.send(f"User {user.mention} has been granted bot management permissions.", ephemeral=True)
        else:
            await ctx.send(f"User {user.mention} already has bot management permissions.", ephemeral=True)

    @manage_group.subcommand(sub_cmd_name="unpermit", sub_cmd_description="Revokes a user's bot management permissions.")
    @slash_option("user", "The user to revoke permissions from", opt_type=OptionType.USER, required=True)
    async def manage_unpermit(self, ctx: SlashContext, user):
        if remove_bot_manager(int(user.id)):
            await ctx.send(f"User {user.mention} has had bot management permissions revoked.", ephemeral=True)
        else:
            await ctx.send(f"User {user.mention} does not have bot management permissions.", ephemeral=True)

    @manage_group.subcommand(sub_cmd_name="devmode", sub_cmd_description="Enable or disable developer mode (auto-updates).")
    @slash_option("action", "Enable or disable dev mode", opt_type=OptionType.STRING, required=True, choices=["enable", "disable"])
    async def manage_devmode(self, ctx: SlashContext, action: str):
        if action == "enable":
            set_dev_mode_setting(True)
            await ctx.send("Developer mode (auto-updates) has been **enabled**. The bot will periodically check for and attempt to install updates.", ephemeral=True)
        elif action == "disable":
            set_dev_mode_setting(False)
            await ctx.send("Developer mode (auto-updates) has been **disabled**.", ephemeral=True)
        else:
            await ctx.send("Invalid action. Please choose 'enable' or 'disable'.", ephemeral=True)

def setup(bot: Client):
    AdminCommands(bot)