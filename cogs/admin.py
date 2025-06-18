import os
import platform
import asyncio
import logging
from interactions import slash_command, slash_option, OptionType, Permissions, Embed

from bot_client import bot
from config import OWNER_ID # Still needed for updatebot

@slash_command("updatebot", description="Pulls the latest updates from GitHub (Owner only).")
async def update_bot_command(ctx):
    if ctx.author.id != OWNER_ID:
        await ctx.send("You do not have permission to use this command.", ephemeral=True)
        return
    await ctx.defer(ephemeral=True)

    current_os = platform.system().lower()
    script_name = "update_bot.sh" if "linux" in current_os else "update_bot.ps1"
    executable = "/bin/bash" if "linux" in current_os else "powershell.exe"
    script_args = [] if "linux" in current_os else ['-ExecutionPolicy', 'Bypass', '-File']
    
    script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', script_name)) # Script is in root

    if not os.path.exists(script_path):
        logging.error(f"Update script not found at: {script_path}")
        await ctx.send(f"Error: Update script '{script_name}' not found at `{script_path}`.", ephemeral=True)
        return

    try:
        logging.info(f"User {ctx.author.user.username} initiated bot update using: {executable} {script_path}")
        # In interactions.py v5+, ctx.author is the User/Member object, so ctx.author.username is correct.
        # logging.info(f"User {ctx.author.username} ({ctx.author.id}) initiated bot update using: {executable} {script_path}")

        process = await asyncio.create_subprocess_exec(
            executable, *script_args, script_path,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        stdout_str = stdout.decode('utf-8', errors='ignore')
        stderr_str = stderr.decode('utf-8', errors='ignore')

        response_message = f"🚀 **Update Script Execution ({current_os.capitalize()})** 🚀\n"
        response_message += f"✅ Script executed successfully.\n" if process.returncode == 0 else f"⚠️ Script finished with exit code: {process.returncode}.\n"

        # Max length for combined log sections to fit within Discord's 2000 char limit
        # Boilerplate text is roughly 200-250 chars. Remaining: ~1750. For two sections: ~875 each.
        max_log_section_length = 850

        if stdout_str:
            response_message += f"**Output:**\n```\n{stdout_str[:max_log_section_length]}\n```\n"
            if len(stdout_str) > max_log_section_length:
                response_message += "... (output truncated)\n"
        if stderr_str:
            response_message += f"**Errors:**\n```\n{stderr_str[:max_log_section_length]}\n```\n"
            if len(stderr_str) > max_log_section_length:
                response_message += "... (errors truncated)\n"

        response_message += "\nℹ️ **Please manually restart the bot process to apply any downloaded updates.**"

        if len(response_message) > 2000:
            response_message = (f"🚀 Update script finished with exit code: {process.returncode}. "
                                f"Logs were too long to display here. Please check the console/logs. "
                                "Manually restart the bot to apply updates.")
        await ctx.send(response_message, ephemeral=True)

    except Exception as e:
        logging.error(f"Error executing update script: {e}", exc_info=True)
        await ctx.send(f"An error occurred: {e}", ephemeral=True)

@slash_command("restartbot", description="Shuts down the bot (Manage Server permission needed).", default_member_permissions=Permissions.MANAGE_GUILD)
async def restart_bot_command(ctx):
    logging.info(f"Restart command initiated by {ctx.author.user.username} ({ctx.author.id}).")
    await ctx.send(
        "✅ Bot shutdown initiated. Manual restart of the process is required.",
        ephemeral=True
    )
    await bot.stop()