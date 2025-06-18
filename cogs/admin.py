import os
import platform
import asyncio
import logging
from interactions import slash_command, slash_option, OptionType, Permissions, Embed

from bot_client import bot
from config import OWNER_ID
from utils.permissions import load_bot_managers, save_bot_managers

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
        process = await asyncio.create_subprocess_exec(
            executable, *script_args, script_path,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        response_message = f"🚀 **Update Script Execution ({current_os.capitalize()})** 🚀\n"
        response_message += f"✅ Script executed successfully.\n" if process.returncode == 0 else f"⚠️ Script finished with exit code: {process.returncode}.\n"
        if stdout: response_message += f"**Output:**\n```\n{stdout.decode('utf-8', errors='ignore')[:1500]}\n```\n"
        if stderr: response_message += f"**Errors:**\n```\n{stderr.decode('utf-8', errors='ignore')[:1500]}\n```\n"
        response_message += "\nℹ️ **Please manually restart the bot process to apply any downloaded updates.**"
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

@slash_command("permit", description="Grants a user bot management permissions (Server Administrator only).", default_member_permissions=Permissions.ADMINISTRATOR)
@slash_option("user", "The user to grant permissions to.", opt_type=OptionType.USER, required=True)
async def permit_command(ctx, user): # user type is resolved by interactions.py
    target_user_id = int(user.id)
    managers = load_bot_managers()
    if target_user_id in managers:
        await ctx.send(f"{user.mention} already has bot management permissions.", ephemeral=True)
        return
    managers.append(target_user_id)
    save_bot_managers(managers)
    logging.info(f"User {ctx.author.user.username} granted bot management to {user.username} ({target_user_id}).")
    await ctx.send(f"✅ {user.mention} has been granted bot management permissions.", ephemeral=True)

@slash_command("unpermit", description="Revokes bot management permissions (Server Administrator only).", default_member_permissions=Permissions.ADMINISTRATOR)
@slash_option("user", "The user to revoke permissions from.", opt_type=OptionType.USER, required=True)
async def unpermit_command(ctx, user):
    target_user_id = int(user.id)
    managers = load_bot_managers()
    if target_user_id not in managers:
        await ctx.send(f"{user.mention} does not have bot management permissions.", ephemeral=True)
        return
    managers.remove(target_user_id)
    save_bot_managers(managers)
    logging.info(f"User {ctx.author.user.username} revoked bot management from {user.username} ({target_user_id}).")
    await ctx.send(f"✅ {user.mention}'s bot management permissions have been revoked.", ephemeral=True)

@slash_command("listmanagers", description="Lists users with bot management permissions (Server Administrator only).", default_member_permissions=Permissions.ADMINISTRATOR)
async def listmanagers_command(ctx):
    managers = load_bot_managers()
    if not managers:
        await ctx.send("No designated bot managers (besides the Bot Owner).", ephemeral=True)
        return
    embed = Embed(title="👑 Bot Managers", color=0xFFD700)
    manager_mentions = []
    for user_id in managers:
        try:
            user_obj = await bot.fetch_user(user_id)
            manager_mentions.append(f"{user_obj.mention} (`{user_obj.username}` - ID: `{user_id}`)")
        except Exception: manager_mentions.append(f"<@{user_id}> (ID: `{user_id}` - Error fetching details)")
    embed.description = "\n".join(manager_mentions)
    embed.set_footer(text=f"The Bot Owner (<@{OWNER_ID}>) always has full permissions.")
    await ctx.send(embeds=embed, ephemeral=True)