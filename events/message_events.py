import logging
import random
import datetime
from typing import Optional

from interactions import Extension, Message, Embed, listen
from interactions.models.discord.channel import GuildText
from interactions.api.events.discord import MessageCreate
from config import SILLY_MENTION_RESPONSES
from settings_manager import get_logging_setting

logger = logging.getLogger(__name__)

# Helper function for logging server activity.
# This function is duplicated in guild_events.py for now.
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

class MessageEvents(Extension):
    def __init__(self, bot):
        self.bot = bot

    @listen()
    async def on_message_create(self, event: MessageCreate):
        """Handles new messages, specifically for bot mentions."""
        message: Message = event.message

        if not message:
            return
        # Defensive check if message is not actually a Message object
        if not isinstance(message, Message):
            logger.warning(f"on_message_create: Extracted message is not of type Message. Type: {type(message)}. Value: {message}")
            return

        author = getattr(message, "author", None)
        if not author or getattr(author, "bot", False):
            return
        bot_self = getattr(self.bot, "me", None) or getattr(self.bot, "user", None)
        if not bot_self or not hasattr(bot_self, "id"):
            return
        bot_id = str(getattr(bot_self, "id", None))
        mentions = getattr(message, "mentions", []) or []
        mentioned_ids = {str(m.id) for m in mentions if hasattr(m, 'id')}
        content = getattr(message, "content", "") or getattr(message, "text", "")
        if bot_id in mentioned_ids or f"<@{bot_id}>" in content:
            channel_id = getattr(message, "channel_id", None)
            if channel_id:
                channel = await self.bot.fetch_channel(channel_id)
                # Only send if channel supports send (GuildText, not GuildForum, GuildCategory, or None)
                if channel and hasattr(channel, 'send') and isinstance(channel, GuildText):
                    await channel.send(random.choice(SILLY_MENTION_RESPONSES))

    @listen()
    async def on_message_delete(self, message: Message):
        if not isinstance(message, Message):
            logger.warning(f"on_message_delete received non-Message object: {type(message)}. Value: {message}")
            return
            
        if not getattr(message, 'guild', None): # Only log guild messages
            return

        content = message.content if message.content else "[Content not available or message was an embed]"
        if len(content) > 1000: # Truncate long messages
            content = content[:1000] + "..."

        embed = Embed(
            title="🗑️ Message Deleted",
            color=0xFF0000, # Red
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.add_field(name="Author", value=f"{message.author.mention} (`{message.author.id}`)", inline=True)
        embed.add_field(name="Channel", value=message.channel.mention, inline=True)
        embed.add_field(name="Content", value=f"```{content}```", inline=False)
        if message.attachments:
            embed.add_field(name="Attachments", value=f"{len(message.attachments)} attachment(s)", inline=True)
        embed.set_footer(text=f"Message ID: {message.id}")

        await _log_server_activity(str(message.guild.id), embed)

    @listen()
    async def on_message_update(self, before: Optional[Message] = None, after: Optional[Message] = None):
        if not after:
            return # Exit if 'after' is None

        if not after or not isinstance(after, Message):
            logger.warning(f"on_message_update called without valid 'after' message. Before: {before}, After: {after}")
            return
        if before is not None and not isinstance(before, Message):
            logger.warning(f"on_message_update: 'before' is not None and not a Message object. Type: {type(before)}, Value: {before}")

        if not getattr(after, 'guild', None) or not getattr(after, 'author', None) or getattr(after.author, 'bot', True):
            return
        if before and getattr(before, 'content', None) == getattr(after, 'content', None) and not (getattr(before, 'embeds', []) != getattr(after, 'embeds', [])):
            return

        old_content = before.content if before and before.content else "[Content not available or was an embed]"
        new_content = after.content if after.content else "[Content not available or is an embed]"

        if len(old_content) > 450: old_content = old_content[:450] + "..."
        if len(new_content) > 450: new_content = new_content[:450] + "..."

        embed = Embed(
            title="✏️ Message Edited",
            description=f"Jump to Message",
            color=0x007FFF, # Blue
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.add_field(name="Author", value=f"{after.author.mention} (`{after.author.id}`)", inline=True)
        embed.add_field(name="Channel", value=after.channel.mention, inline=True)
        embed.add_field(name="Before", value=f"```{old_content}```", inline=False)
        embed.add_field(name="After", value=f"```{new_content}```", inline=False)
        embed.set_footer(text=f"Message ID: {after.id}")

        await _log_server_activity(str(after.guild.id), embed)

def setup(bot):
    MessageEvents(bot)