import logging
import os
import asyncio
import subprocess
import sys

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
    @slash_option("action", "Enable or disable dev mode", opt_type=OptionType.STRING, required=True, choices=[{"name": "Enable", "value": "enable"}, {"name": "Disable", "value": "disable"}])
    async def manage_devmode(self, ctx: SlashContext, action: str):
        if action == "enable":
            set_dev_mode_setting(True)
            await ctx.send("Developer mode (auto-updates) has been **enabled**. The bot will periodically check for and attempt to install updates.", ephemeral=True)
        elif action == "disable":
            set_dev_mode_setting(False)
            await ctx.send("Developer mode (auto-updates) has been **disabled**.", ephemeral=True)

    @manage_group.subcommand(sub_cmd_name="update", sub_cmd_description="Pulls the latest updates from Git and restarts the bot.")
    async def manage_update(self, ctx: SlashContext):
        """Pulls the latest updates from Git and restarts the bot."""
        await ctx.send("Attempting to pull the latest updates from Git... The bot will restart shortly.", ephemeral=True)
        
        try:
            # The update script is expected to handle everything, including killing the current process.
            # We use Popen to detach the process so it can continue running even after the bot script exits.
            # By explicitly calling '/bin/bash', we avoid "Permission Denied" errors if the script loses its execute bit.
            subprocess.Popen(['/bin/bash', './update_bot.sh'])
            await asyncio.sleep(2) # Give the script a moment to start
            logger.info(f"Update initiated by {ctx.author.user}. Shutting down to allow update script to take over.")
            await self.bot.stop()
        except Exception as e:
            logger.error(f"Failed to initiate update: {e}", exc_info=True)
            await ctx.edit(content=f"An error occurred while trying to start the update process: {e}")

    @manage_group.subcommand(sub_cmd_name="restart", sub_cmd_description="Restarts the bot.")
    async def manage_restart(self, ctx: SlashContext):
        """Restarts the bot process."""
        await ctx.send("Restarting... Be right back!", ephemeral=True)
        logger.info(f"Restart initiated by {ctx.author.user}. Shutting down.")
        await self.bot.stop()

def setup(bot: Client):
    AdminCommands(bot)