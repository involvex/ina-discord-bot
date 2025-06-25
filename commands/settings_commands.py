import logging
from typing import Optional, List, Dict, Any

from interactions import Extension, slash_command, slash_option, SlashContext, User, Permissions, OptionType, ChannelType, Embed
from interactions.models.discord.channel import GuildText # For specific channel type checking

from settings_manager import (
    save_welcome_setting, get_welcome_setting,
    save_logging_setting, get_logging_setting,
    is_bot_manager, add_bot_manager, remove_bot_manager, load_bot_managers
)
from config import OWNER_ID # Assuming OWNER_ID is in config.py

logger = logging.getLogger(__name__)

class SettingsCommands(Extension):
    def __init__(self, bot):
        self.bot = bot

    @slash_command(name="settings", description="Manage bot settings (requires permissions).")
    async def settings_group(self, ctx: SlashContext):
        """Base command for settings. Discord will typically show subcommands."""
        pass

    @settings_group.subcommand(sub_cmd_name="permit", sub_cmd_description="Grants a user bot management permissions.")
    @slash_option("user", "The user to grant permissions to.", opt_type=OptionType.USER, required=True)
    async def settings_permit_subcommand(self, ctx: SlashContext, user: User):
        if not ctx.author.has_permission(Permissions.ADMINISTRATOR) and ctx.author.id != OWNER_ID:
            await ctx.send("You need Administrator permissions or be the Bot Owner to use this command.", ephemeral=True)
            return

        if add_bot_manager(int(user.id)):
            await ctx.send(f"✅ {user.mention} has been granted bot management permissions.", ephemeral=True)
        else:
            await ctx.send(f"ℹ️ {user.mention} already has bot management permissions.", ephemeral=True)

    @settings_group.subcommand(sub_cmd_name="unpermit", sub_cmd_description="Revokes a user's bot management permissions.")
    @slash_option("user", "The user to revoke permissions from.", opt_type=OptionType.USER, required=True)
    async def settings_unpermit_subcommand(self, ctx: SlashContext, user: User):
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

    @settings_group.subcommand(sub_cmd_name="listmanagers", sub_cmd_description="Lists users with bot management permissions.")
    async def settings_listmanagers_subcommand(self, ctx: SlashContext):
        if not ctx.author.has_permission(Permissions.ADMINISTRATOR) and not is_bot_manager(int(ctx.author.id)) and ctx.author.id != OWNER_ID :
            await ctx.send("You need Administrator permissions or be a Bot Manager/Owner to use this command.", ephemeral=True)
            return

        managers = load_bot_managers()
        embed = Embed(title="👑 Bot Managers 👑", color=0xFFD700) # Gold color

        owner_user = await self.bot.fetch_user(OWNER_ID) # Use self.bot.fetch_user
        if owner_user:
            embed.add_field(name="Bot Owner (Implicit Manager)", value=owner_user.mention, inline=False)
        else:
            embed.add_field(name="Bot Owner (Implicit Manager)", value=f"ID: {OWNER_ID} (User not found)", inline=False)

        if managers:
            manager_mentions = []
            for manager_id in managers:
                if manager_id == OWNER_ID: continue # Skip owner if already listed
                try:
                    user = await self.bot.fetch_user(manager_id) # Use self.bot.fetch_user
                    manager_mentions.append(user.mention if user else f"ID: {manager_id} (User not found)")
                except Exception:
                    manager_mentions.append(f"ID: {manager_id} (Error fetching user)")
            embed.add_field(name="Permitted Managers", value="\n".join(manager_mentions) if manager_mentions else "No additional managers permitted.", inline=False)
        else:
            embed.add_field(name="Permitted Managers", value="No additional managers permitted.", inline=False)
        await ctx.send(embeds=embed, ephemeral=True)

    @settings_group.subcommand(
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
        required=False,
        channel_types=[ChannelType.GUILD_TEXT]
    )
    async def settings_welcomemessages_manager(self, ctx: SlashContext, action: str, channel: Optional[GuildText] = None):
        if not ctx.author.has_permission(Permissions.MANAGE_GUILD) and not is_bot_manager(int(ctx.author.id)):
            await ctx.send("You need 'Manage Server' permission or be a Bot Manager/Owner to use this command.", ephemeral=True)
            return
        if not ctx.guild:
            await ctx.send("This command can only be used in a server.", ephemeral=True)
            return

        action = action.lower()

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
                    welcome_channel_obj = await self.bot.fetch_channel(int(setting['channel_id']))
                    await ctx.send(f"ℹ️ Welcome messages are **enabled** and set to channel {welcome_channel_obj.mention}.", ephemeral=True)
                except Exception:
                    await ctx.send(f"ℹ️ Welcome messages are **enabled** and set to channel ID `{setting['channel_id']}` (channel might be deleted or inaccessible).", ephemeral=True)
            else:
                await ctx.send("ℹ️ Welcome messages are currently **disabled** for this server.", ephemeral=True)
        else:
            await ctx.send("Invalid action specified. Please use 'enable', 'disable', or 'status'.", ephemeral=True)

    @settings_group.subcommand(
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
        required=False,
        channel_types=[ChannelType.GUILD_TEXT]
    )
    async def settings_logging_manager(self, ctx: SlashContext, action: str, channel: Optional[GuildText] = None):
        if not ctx.author.has_permission(Permissions.MANAGE_GUILD) and not is_bot_manager(int(ctx.author.id)):
            await ctx.send("You need 'Manage Server' permission or be a Bot Manager/Owner to use this command.", ephemeral=True)
            return
        if not ctx.guild:
            await ctx.send("This command can only be used in a server.", ephemeral=True)
            return

        action = action.lower()

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
                    log_channel_obj = await self.bot.fetch_channel(int(setting['channel_id']))
                    await ctx.send(f"ℹ️ Server activity logging is **enabled** and set to channel {log_channel_obj.mention}.", ephemeral=True)
                except Exception:
                    await ctx.send(f"ℹ️ Server activity logging is **enabled** and set to channel ID `{setting['channel_id']}` (channel might be deleted or inaccessible).", ephemeral=True)
            else:
                await ctx.send("ℹ️ Server activity logging is currently **disabled** for this server.", ephemeral=True)
        else:
            await ctx.send("Invalid action specified. Please use 'enable', 'disable', or 'status'.", ephemeral=True)

def setup(bot):
    SettingsCommands(bot)