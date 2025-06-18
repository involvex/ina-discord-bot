import asyncio
import logging
import random
import requests
import packaging.version

from interactions import Activity, ActivityType
from bot_client import bot
from config import (
    __version__,
    NW_FUNNY_STATUSES,
    BOT_INVITE_URL,
    GITHUB_REPO_OWNER,
    GITHUB_REPO_NAME,
    GITHUB_VERSION_FILE_URL,
    UPDATE_CHECK_INTERVAL_SECONDS
)
from interactions import TextChannel # For type checking channel
from interactions.api import events # For GuildMemberAdd event type
from utils.settings_manager import get_guild_setting
from config import NEW_WORLD_WELCOME_MESSAGES

async def rotate_funny_presence(client_instance, interval=60):
    await client_instance.wait_until_ready()
    while True:
        status = random.choice(NW_FUNNY_STATUSES)
        funny_status = f"{status['name']} – {status['state']}"
        activity_buttons = [{"label": "Add Ina's Bot to your Server", "url": BOT_INVITE_URL}]
        try:
            await client_instance.change_presence(activity=Activity(name=funny_status, type=ActivityType.GAME, buttons=activity_buttons))
        except Exception as e:
            logging.warning(f"Failed to set presence: {e}")
        await asyncio.sleep(interval)

async def check_for_updates_task(client_instance):
    await client_instance.wait_until_ready()
    logging.info(f"Ina's New World Bot version: {__version__} starting update checks.")
    while True:
        try:
            headers = {"Accept": "application/vnd.github.v3+json"}
            response = requests.get(GITHUB_VERSION_FILE_URL, headers=headers, timeout=15)

            if response.status_code == 404:
                logging.info(f"VERSION file not found on main branch at {GITHUB_VERSION_FILE_URL}. Update check skipped.")
            elif response.status_code == 200:
                latest_version_str = response.text.strip()
                update_source_url = f"https://github.com/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/tree/main"

                if latest_version_str:
                    current_v = packaging.version.parse(__version__)
                    latest_v = packaging.version.parse(latest_version_str)
                    logging.debug(f"Update Check: Current bot version: {current_v}, Latest version on main branch: {latest_v}")
                    if latest_v > current_v:
                        logging.warning(
                            f"🎉 A new version of Ina's New World Bot is available: {latest_v} "
                            f"(current: {current_v}). Restart the bot to apply the update. Source: {update_source_url}"
                        )
                    else:
                        logging.info("Bot is up to date with the version on the main branch.")
                else:
                    logging.warning(f"VERSION file at {GITHUB_VERSION_FILE_URL} is empty or invalid.")
            else:
                logging.error(f"Failed to fetch latest release info. Status: {response.status_code}, Response: {response.text[:200]}")
        except requests.exceptions.RequestException as e:
            logging.error(f"Network error during GitHub update check: {e}")
        except packaging.version.InvalidVersion as e:
            logging.error(f"Error parsing version string during update check: {e}")
        except Exception as e:
            logging.error(f"An unexpected error occurred during GitHub update check: {e}", exc_info=True)
        await asyncio.sleep(UPDATE_CHECK_INTERVAL_SECONDS)

@bot.event()
async def on_ready():
    logging.info(f"{bot.user.username} is online and ready!")
    asyncio.create_task(rotate_funny_presence(bot, interval=60))
    asyncio.create_task(check_for_updates_task(bot))

@bot.event()
async def on_message_create(event): # Renamed 'message' to 'event' for clarity with interactions.py v5
    message_obj = getattr(event, "message", event) # Adapt for different event structures
    if not message_obj or not hasattr(message_obj, "author") or getattr(message_obj.author, "bot", False):
        return
    if not bot.user or not hasattr(bot.user, "id"): return

    bot_id_str = str(bot.user.id)
    mentioned_ids = {str(m.id) for m in getattr(message_obj, "mentions", []) if hasattr(m, 'id')}
    content = getattr(message_obj, "content", "")

    if bot_id_str in mentioned_ids or f"<@{bot_id_str}>" in content or f"<@!{bot_id_str}>" in content:
        if hasattr(message_obj, "channel") and hasattr(message_obj.channel, "send"): # Check if channel object exists and has send
            await message_obj.channel.send("👋 The winds of Aeternum greet you! Use `/help` to see my commands.")

@bot.event(name="on_guild_member_add")
async def on_member_join_event(event: events.GuildMemberAdd):
    member = event.member
    if not member.guild:
        return

    guild_id_str = str(member.guild.id)
    current_logger = logging.getLogger(__name__) # Use a logger instance

    current_logger.info(f"Member {member.username} ({member.id}) joined guild {member.guild.name} ({guild_id_str})")

    is_enabled = get_guild_setting(guild_id_str, "welcome_enabled", False)
    channel_id_str = get_guild_setting(guild_id_str, "welcome_channel_id")

    if is_enabled and channel_id_str:
        try:
            channel_id = int(channel_id_str)
            target_channel = await bot.fetch_channel(channel_id)

            if target_channel and isinstance(target_channel, TextChannel):
                welcome_message_template = random.choice(NEW_WORLD_WELCOME_MESSAGES)
                formatted_message = welcome_message_template.format(mention=member.mention)
                await target_channel.send(formatted_message)
                current_logger.info(f"Sent welcome message to {member.username} in {target_channel.name} for guild {guild_id_str}")
            elif target_channel:
                current_logger.warning(f"Welcome channel {channel_id_str} for guild {guild_id_str} is not a text channel.")
            else:
                current_logger.warning(f"Could not fetch welcome channel {channel_id_str} for guild {guild_id_str}.")
        except ValueError:
            current_logger.error(f"Invalid channel ID format '{channel_id_str}' for guild {guild_id_str}.")
        except Exception as e:
            current_logger.error(f"Error sending welcome message for guild {guild_id_str}: {e}", exc_info=True)
    elif is_enabled: # No channel set
        current_logger.info(f"Welcome messages enabled for guild {guild_id_str} but no channel is set.")