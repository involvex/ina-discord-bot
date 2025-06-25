import logging
import asyncio
import packaging.version
import requests
import os
import subprocess
import platform
import aiohttp
import json

from interactions import Extension, slash_command, slash_option, SlashContext, Permissions, Client, OptionType, Embed, listen
from config import OWNER_ID, GITHUB_REPO_OWNER, GITHUB_REPO_NAME, GITHUB_VERSION_FILE_URL, UPDATE_CHECK_INTERVAL_SECONDS, __version__ as config_version
from common_utils import _cleanup_cache_files_recursive
from settings_manager import is_bot_manager

logger = logging.getLogger(__name__)

class AdminCommands(Extension):
    """A simple extension for admin-only commands."""

    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__) # Initialize logger for the instance
    
    @listen()
    async def on_ready(self):
        # Schedule the update check task when the bot is ready
        # This ensures the event loop is running and bot.user is available
        asyncio.create_task(self.check_for_updates())

    async def _perform_update_and_restart(self, slash_ctx: SlashContext = None):
        """
        Handles the bot update process: executes the update script and stops the bot for restart.
        If slash_ctx is provided, sends feedback to the command invoker.
        Returns True if update script succeeded and bot stop was initiated, False otherwise.
        """
        current_os = platform.system().lower()
        script_name = ""
        executable = ""

        if "windows" in current_os:
            script_name = "update_bot.ps1"
            executable = "powershell.exe"
            script_args = ['-ExecutionPolicy', 'Bypass', '-File']
        elif "linux" in current_os:
            script_name = "update_bot.sh"
            executable = "/bin/bash"
            script_args = []
        else:
            if slash_ctx:
                await slash_ctx.send(f"Unsupported operating system for automatic updates: {current_os}", ephemeral=True)
            logger.error(f"Unsupported operating system for automatic updates: {current_os}")
            return False

        script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', script_name)) # Go up one level to project root

        if not os.path.exists(script_path):
            error_msg = f"Update script not found at: {script_path}"
            logger.error(error_msg)
            if slash_ctx:
                await slash_ctx.send(f"Error: Update script not found at the expected location: `{script_path}`.", ephemeral=True)
            return False

        initiator_desc = "Automatic update check"
        if slash_ctx and slash_ctx.author:
            initiator_desc = f"User {slash_ctx.author.username} ({slash_ctx.author.id})"

        try:
            logger.info(f"{initiator_desc} initiated bot update using {executable} with script: {script_path}")
            process = await asyncio.create_subprocess_exec(
                executable,
                *script_args,
                script_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            stdout_str = stdout.decode('utf-8', errors='ignore')
            stderr_str = stderr.decode('utf-8', errors='ignore')

            if slash_ctx:
                response_message = f"🚀 **Update Script Execution ({current_os.capitalize()})** 🚀\n"
                if process.returncode == 0:
                    response_message += "✅ Script executed successfully.\n"
                else:
                    response_message += f"⚠️ Script finished with exit code: {process.returncode}.\n"
                
                max_log_section_length = 850

                if stdout_str:
                    response_message += f"**Output:**\n```\n{stdout_str[:max_log_section_length]}\n```\n"
                    if len(stdout_str) > max_log_section_length:
                        response_message += f"... (output truncated)\n"
                if stderr_str:
                    response_message += f"**Errors:**\n```\n{stderr_str[:max_log_section_length]}\n```\n"
                    if len(stderr_str) > max_log_section_length:
                        response_message += f"... (errors truncated)\n"
                
                if process.returncode == 0:
                    response_message += "\n✅ **Updates pulled. Attempting to apply by restarting the bot...**\n"
                    response_message += "ℹ️ The bot will shut down. An external process manager (e.g., PM2, systemd, Docker restart policy) is required to bring it back online with the updates."
                else:
                    response_message += "\n❌ **Update script failed. Bot will not restart.**"

                if len(response_message) > 2000:
                    response_message = (f"🚀 Update script finished with exit code: {process.returncode}. "
                                        f"Logs were too long to display here. Please check the console/logs. ")
                    if process.returncode == 0:
                        response_message += "Bot will attempt to restart to apply updates."
                    else:
                        response_message += "Bot will not restart."
                await slash_ctx.send(response_message, ephemeral=True)

            if process.returncode == 0:
                logger.info(f"Update script successful for {initiator_desc}. Stopping bot to apply updates.")
                if slash_ctx: await asyncio.sleep(3)
                await self.bot.stop()
                if not slash_ctx:
                    logger.warning(f"Automatic update successful. Bot has been stopped for restart by process manager.")
                return True
            else:
                log_msg = f"Update script failed for {initiator_desc} with exit code {process.returncode}."
                if stdout: log_msg += f" Stdout: {stdout.decode(errors='ignore')}"
                if stderr: log_msg += f" Stderr: {stderr.decode(errors='ignore')}"
                logger.error(log_msg)
                if not slash_ctx:
                    logger.error(f"Automatic update failed. Script exit code: {process.returncode}.")
                return False
        except Exception as e:
            error_msg = f"An error occurred while {initiator_desc} tried to run update script '{script_name}': {e}"
            logger.error(error_msg, exc_info=True)
            if slash_ctx:
                await slash_ctx.send(error_msg, ephemeral=True)
            return False

    async def check_for_updates(self):
        """Periodically checks GitHub for new bot releases and logs a notification if found."""
        await self.bot.wait_until_ready()
        logger.info(f"Ina's New World Bot version: {config_version} starting update checks.")
        while True:
            try:
                headers = {"Accept": "application/vnd.github.v3+json"}
                response = requests.get(GITHUB_VERSION_FILE_URL, headers=headers, timeout=15)

                if response.status_code == 404:
                    logger.info(f"VERSION file not found on main branch at {GITHUB_VERSION_FILE_URL}. Update check skipped.")
                elif response.status_code == 200:
                    latest_version_str = response.text.strip()
                    update_source_url = f"https://github.com/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/tree/main"

                    if latest_version_str:
                        current_v = packaging.version.parse(config_version)
                        latest_v = packaging.version.parse(latest_version_str)

                        logger.debug(f"Update Check: Current bot version: {current_v}, Latest version on main branch: {latest_v}")

                        if latest_v > current_v:
                            logger.warning(
                                f"🎉 A new version of Ina's New World Bot is available: {latest_v} "
                                f"(current: {current_v}). Attempting automatic update and restart. Source: {update_source_url}"
                            )
                            await self._perform_update_and_restart()
                        else:
                            logger.info("Bot is up to date with the version on the main branch.")
                    else:
                        logger.warning(f"VERSION file at {GITHUB_VERSION_FILE_URL} is empty or invalid.")
                else:
                    logger.error(
                        f"Failed to fetch latest release info from GitHub. Status: {response.status_code}, "
                        f"Response: {response.text[:200]}"
                    )
            except requests.exceptions.RequestException as e:
                logger.error(f"Network error during GitHub update check: {e}")
            except packaging.version.InvalidVersion as e:
                logger.error(f"Error parsing version string during update check: {e}")
            except Exception as e:
                logger.error(f"An unexpected error occurred during GitHub update check: {e}", exc_info=True)
            
            await asyncio.sleep(UPDATE_CHECK_INTERVAL_SECONDS)

    @slash_command(name="manage", description="Manage bot operations (restricted).")
    async def manage_group(self, ctx: SlashContext):
        """Base command for bot management."""
        pass

    @manage_group.subcommand(
        sub_cmd_name="update",
        sub_cmd_description="Pulls updates from GitHub and restarts the bot (Owner only)."
    )
    async def manage_update(self, ctx: SlashContext):
        if ctx.author.id != OWNER_ID:
            await ctx.send("You do not have permission to use this command.", ephemeral=True)
            return

        await ctx.defer(ephemeral=True)
        await self._perform_update_and_restart(slash_ctx=ctx)

    @manage_group.subcommand(
        sub_cmd_name="restart",
        sub_cmd_description="Shuts down the bot for manual restart (Bot Owner/Manager only)."
    )
    async def manage_restart(self, ctx: SlashContext):
        if not is_bot_manager(int(ctx.author.id)) and ctx.author.id != OWNER_ID:
            await ctx.send("You do not have permission to use this command.", ephemeral=True)
            return

        guild_info = "a Direct Message"
        if ctx.guild:
            guild_info = f"guild {ctx.guild.name} ({ctx.guild.id})"

        self.logger.info(f"Restart command initiated by {ctx.author.username} ({ctx.author.id}) in {guild_info}.")

        await ctx.send(
            "✅ Bot shutdown command acknowledged. "
            "The bot process will now attempt to stop.\n"
            "ℹ️ **A manual restart of the bot's process on the server is required for it to come back online.**",
            ephemeral=True
        )
        await self.bot.stop()

    @manage_group.subcommand(
        sub_cmd_name="cleanup",
        sub_cmd_description="Cleans up cached Python files (__pycache__, .pyc) (Bot Owner/Manager only)."
    )
    async def manage_cleanup(self, ctx: SlashContext):
        if not is_bot_manager(int(ctx.author.id)) and ctx.author.id != OWNER_ID:
            await ctx.send("You do not have permission to use this command.", ephemeral=True)
            return

        await ctx.defer(ephemeral=True)

        project_root = os.path.dirname(os.path.abspath(__file__))
        pycache_count, pyc_count, errors = await _cleanup_cache_files_recursive(project_root)

        files_to_remove = [
            "items.csv", "perks.csv", "perks_scraped.csv", "perks_buddy.csv", "items.json", "new_world_world_data.db"
        ]
        removed_files = []
        for filename in files_to_remove:
            file_path = os.path.join(project_root, filename)
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    removed_files.append(filename)
                except Exception as e:
                    errors.append(f"Failed to remove {filename}: {e}")

        response_message = "🧹 **Cache Cleanup Report** 🧹\n"
        response_message += f"Removed `{pycache_count}` `__pycache__` directories.\n"
        response_message += f"Removed `{pyc_count}` `.pyc` files.\n"
        if removed_files:
            response_message += f"Removed data files: {', '.join(removed_files)}\n"

        if errors:
            response_message += "\n⚠️ **Errors Encountered:**\n"
            for error in errors[:5]:
                response_message += f"- {error}\n"
            if len(errors) > 5:
                response_message += f"- ...and {len(errors) - 5} more errors (check bot logs for details).\n"
        else:
            response_message += "\n✅ Cleanup completed successfully with no errors."

        await ctx.send(response_message, ephemeral=True)

    async def update_items_from_nwdb(self):
        """Scrapes all item pages from nwdb.info and saves them to items_updated.json."""
        all_items = []
        page = 1
        page_count = 1
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        async with aiohttp.ClientSession(headers=headers) as session:
            while page <= page_count:
                url = f"https://nwdb.info/db/items/page/{page}.json"
                logger.info(f"Scraping item page: {url}")
                try:
                    async with session.get(url, timeout=20) as resp:
                        if resp.status != 200:
                            body = await resp.text()
                            logger.error(f"Failed to fetch item page {page}, status: {resp.status}. Body: {body[:200]}")
                            break

                        data = await resp.json(content_type=None)

                        if not data.get('success') or not isinstance(data.get('data'), list):
                            logger.warning(f"Response from {url} was not successful or did not contain a data list.")
                            break

                        if page == 1 and data.get('pageCount'):
                            page_count = data['pageCount']
                            logger.info(f"Total item pages to scrape: {page_count}")

                        all_items.extend(data['data'])
                        page += 1
                        await asyncio.sleep(0.5)
                except Exception as e:
                    logger.error(f"An unexpected error occurred during page {page} scrape: {e}", exc_info=True)
                    break
        with open("items_updated.json", "w", encoding="utf-8") as f:
            json.dump(all_items, f, indent=2)
        logger.info(f"Finished scraping. Total items saved: {len(all_items)}")
        return len(all_items)

    @manage_group.subcommand(
        sub_cmd_name="update_items",
        sub_cmd_description="Scrape all items from nwdb.info and upload to git (Owner only)."
    )
    async def manage_update_items(self, ctx: SlashContext):
        if ctx.author.id != OWNER_ID:
            await ctx.send("You do not have permission to use this command.", ephemeral=True)
            return
        await ctx.defer(ephemeral=True)
        await ctx.send("Starting item scrape from nwdb.info... this may take a moment.", ephemeral=True)
        count = await self.update_items_from_nwdb()
        if count == 0:
            await ctx.send("Scraped 0 items. No changes to commit.", ephemeral=True)
            return
        try:
            git_status_result = subprocess.run(["git", "status", "--porcelain", "items_updated.json"], capture_output=True, text=True, check=True)
            if not git_status_result.stdout.strip():
                await ctx.send(f"Scraped {count} items, but there are no changes to commit. The local file is already up-to-date.", ephemeral=True)
                return
            subprocess.run(["git", "add", "items_updated.json"], check=True)
            commit_message = f"Update items_updated.json ({count} items scraped from nwdb.info)"
            subprocess.run(["git", "commit", "-m", commit_message], check=True)
            subprocess.run(["git", "push"], check=True)
            await ctx.send(f"✅ Scraped and uploaded {count} items to items_updated.json and pushed to git.", ephemeral=True)
        except subprocess.CalledProcessError as e:
            error_output = e.stderr or e.stdout or "No output from command."
            await ctx.send(f"Scraped {count} items, but a git command failed: {e}\n```\n{error_output}\n```", ephemeral=True)
        except Exception as e:
            await ctx.send(f"An unexpected error occurred during git operations: {e}", ephemeral=True)

    @manage_group.subcommand(
        sub_cmd_name="debug",
        sub_cmd_description="Enable or disable debug logging in the console (Bot Owner/Manager only)."
    )
    @slash_option(
        name="action",
        description="Choose to enable or disable debug logging.",
        opt_type=OptionType.STRING,
        required=True,
        choices=[
            {"name": "Enable Debug Logging", "value": "enable"},
            {"name": "Disable Debug Logging", "value": "disable"},
        ]
    )
    async def manage_debug(self, ctx: SlashContext, action: str):
        from config import DEFAULT_LOG_LEVEL # Only need DEFAULT_LOG_LEVEL for setting info level
        if not is_bot_manager(int(ctx.author.id)) and ctx.author.id != OWNER_ID:
            await ctx.send("You do not have permission to use this command.", ephemeral=True)
            return

        action = action.lower()
        root_logger = logging.getLogger()
        interactions_logger = logging.getLogger("interactions")

        if action == "enable":
            root_logger.setLevel(logging.DEBUG)
            interactions_logger.setLevel(logging.DEBUG)
            await ctx.send("⚙️ Debug logging **enabled**. Console will now show verbose logs.", ephemeral=True)
            logger.debug("Debug mode has been enabled via command.")
        elif action == "disable":
            root_logger.setLevel(DEFAULT_LOG_LEVEL)
            interactions_logger.setLevel(DEFAULT_LOG_LEVEL)
            logger.info("Debug mode has been disabled via command.")
            await ctx.send("⚙️ Debug logging **disabled**. Console will revert to normal verbosity.", ephemeral=True)

def setup(bot: Client):
    AdminCommands(bot)