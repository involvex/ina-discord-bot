import logging
import random
import datetime
from typing import Optional

from interactions import Extension, Member, Embed, User, Role, listen
from interactions.models.discord.channel import GuildText
from config import NEW_WORLD_WELCOME_MESSAGES
from settings_manager import get_welcome_setting, get_logging_setting

logger = logging.getLogger(__name__)

# Helper function for logging server activity.
# This function is duplicated in message_events.py for now.
# For a larger project, consider moving it to a shared utility module (e.g., common_utils.py)
# or a dedicated logging extension if it's used across multiple event types.
async def _log_server_activity(guild_id: str, embed: Embed, text_message: Optional[str] = None):
    """Helper function to send log messages to the configured log channel."""
    if not guild_id:
        return

    log_settings = get_logging_setting(str(guild_id))
    if log_settings and log_settings.get("enabled") and log_settings.get("channel_id"):
        log_channel_id = log_settings["channel_id"]
        try:
            # Use embed._client to get bot instance, as embed objects created by interactions.py
            # typically have a reference to the client.
            log_channel = await embed._client.fetch_channel(int(log_channel_id))
            if log_channel and isinstance(log_channel, GuildText):
                if not embed.timestamp:
                    embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
                await log_channel.send(content=text_message, embeds=embed)
            else:
                logger.warning(f"Log channel {log_channel_id} in guild {guild_id} is not a valid text channel or not found.")
        except Exception as e:
            logger.error(f"Failed to send log message to channel {log_channel_id} in guild {guild_id}: {e}", exc_info=True)

class GuildEvents(Extension):
    def __init__(self, bot):
        self.bot = bot

    @listen()
    async def on_guild_member_add(self, member: Member):
        """Handles new member joins and sends a welcome message if configured."""
        if not member.guild:
            return

        if not isinstance(member, Member):
            logger.error(f"on_guild_member_add received non-Member object for member: {type(member)}. Value: {member}")
            return

        guild_id_str = str(member.guild.id)
        settings = get_welcome_setting(guild_id_str)

        if settings and settings.get("enabled") and settings.get("channel_id"):
            channel_id = settings["channel_id"]
            try:
                channel = await self.bot.fetch_channel(int(channel_id))
                if channel and isinstance(channel, GuildText):
                    welcome_message = random.choice(NEW_WORLD_WELCOME_MESSAGES).format(
                        member_mention=member.mention,
                        guild_name=member.guild.name
                    )
                    await channel.send(welcome_message)
                    logger.info(f"Sent welcome message to {member.username} in guild {member.guild.name} ({guild_id_str}), channel {channel.name} ({channel_id}).")
                else:
                    logger.warning(f"Welcome message channel {channel_id} in guild {guild_id_str} is not a valid text channel or not found.")
            except Exception as e:
                logger.error(f"Failed to send welcome message in guild {guild_id_str}, channel {channel_id}: {e}", exc_info=True)

    @listen()
    async def on_guild_member_remove(self, member: Member):
        if not isinstance(member, Member):
            logger.error(f"on_guild_member_remove received non-Member object: {type(member)}. Value: {member}")
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

    @listen()
    async def on_guild_ban(self, guild_id: str, user: User):
        guild = await self.bot.fetch_guild(guild_id)
        if not guild: return

        if not isinstance(user, User):
            logger.error(f"on_guild_ban received non-User object: {type(user)}. Value: {user}")
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

    @listen()
    async def on_guild_unban(self, guild_id: str, user: User):
        guild = await self.bot.fetch_guild(guild_id)
        if not guild: return

        if not isinstance(user, User):
            logger.error(f"on_guild_unban received non-User object: {type(user)}. Value: {user}")
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

    @listen()
    async def on_guild_role_create(self, role: Role):
        if not isinstance(role, Role):
            logger.error(f"on_guild_role_create received non-Role object: {type(role)}. Value: {role}")
            return

        embed = Embed(
            title="✨ Role Created",
            description=f"Role: {role.mention} (`{role.name}` | `{role.id}`)",
            color=0x00FF00, # Green
        )
        if hasattr(role, 'guild') and role.guild:
            await _log_server_activity(str(role.guild.id), embed)

    @listen()
    async def on_guild_role_delete(self, role: Role):
        if not isinstance(role, Role):
            logger.error(f"on_guild_role_delete received non-Role object: {type(role)}. Value: {role}")
            return

        embed = Embed(
            title="🗑️ Role Deleted",
            description=f"Role Name: `{role.name}` (ID: `{role.id}`)",
            color=0xFF4500, # OrangeRed
        )
        if hasattr(role, 'guild') and role.guild:
            await _log_server_activity(str(role.guild.id), embed)

def setup(bot):
    GuildEvents(bot)