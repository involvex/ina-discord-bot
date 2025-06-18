<p align="center">
  <a href="https://github.com/involvex/ina-discord-bot-">
    <img src="https://raw.githubusercontent.com/involvex/ina-discord-bot-/main/docs/src/images/logo.png" alt="Ina's New World Bot Logo" width="150"/>
  </a>
</p>

<h1 align="center">Ina's New World Bot</h1>

<p align="center">
  Your indispensable <strong>Aeternum</strong> companion for Discord.<br>
  Uncover secrets, manage your arsenal, and conquer the island!
</p>

<p align="center">
  <a href="https://discord.com/oauth2/authorize?client_id=1368579444209352754&scope=bot+applications.commands&permissions=8" target="_blank" rel="noopener">
    <img src="https://img.shields.io/badge/%F0%9F%A4%96%20Invite%20Ina%20to%20Your%20Server-3A6EA5?style=for-the-badge&logo=discord&logoColor=white" alt="Invite Ina to Your Server">
  </a>
</p>

## ✨ Key Features

*   **Deep Dive Database:** Instantly access detailed information on New World items, perks, and recipes. (e.g., `<code>/nwdb</code>`, `<code>/perk</code>`, `<code>/recipe</code>`)
*   **Strategic Crafting:** Calculate materials for crafts, view full recipe breakdowns, and determine exact costs for your crafting endeavors. (e.g., `<code>/calculate_craft</code>`, `<code>/recipe</code>`)
*   **Build Management:** Save, share, and manage your favorite New World builds from `nw-buddy.de`. (e.g., `<code>/build add</code>`, `<code>/build list</code>`)
*   **Server Enhancements:** Enhance your server with optional welcome messages for new members and activity logging.
*   **Aeternum Fun:** Engage with fun commands, including the legendary `<code>/petpet</code>` ritual and more!
*   **Bot Administration:** Tools for bot owners and administrators to manage the bot, including permissions and updates.
*   **Automatic Updates:** Configure Ina to check for and apply updates to herself (requires specific server-side setup).
*   **Always Evolving:** Regularly updated with new features, improvements, and the latest New World game data.

## Commands

Here's a list of available commands. Use `/help [command_name]` in Discord for more details on a specific command.

### General Commands
*   `<code>/ping</code>`: Check if the bot is online.
*   `<code>/help [command_name]</code>`: Show available commands or help for a specific command.
*   `<code>/petpet <user></code>`: Give a New World petting ritual to a user!
*   `<code>/calculate <expression></code>`: Perform a calculation with New World magic!
*   `<code>/about</code>`: Show information about Ina's New World Bot.

### New World Specific Commands
*   `<code>/nwdb <item_name></code>`: Look up items from New World Database.
*   `<code>/perk <perk_name></code>`: Look up information about a specific New World perk.
*   `<code>/recipe <item_name></code>`: Show the full recipe breakdown for a craftable item.
*   `<code>/calculate_craft <item_name> [amount]</code>`: Calculate resources needed to craft an item, including intermediates.

### Build Management
*   `<code>/build add <link> <name> [keyperks]</code>`: Add a build from nw-buddy.de.
*   `<code>/build list</code>`: Show a list of saved builds.
*   `<code>/build remove <name></code>`: Remove a saved build. (Requires: Manage Server or Bot Manager)

### Management & Settings (Require Permissions)
*   `<code>/manage update</code>`: Pulls updates from GitHub and restarts the bot. (Requires: Bot Owner)
*   `<code>/manage restart</code>`: Shuts down the bot for manual restart. (Requires: Bot Owner/Manager)
*   `<code>/settings permit <user></code>`: Grants a user bot management permissions. (Requires: Server Admin or Bot Owner)
*   `<code>/settings unpermit <user></code>`: Revokes a user's bot management permissions. (Requires: Server Admin or Bot Owner)
*   `<code>/settings listmanagers</code>`: Lists users with bot management permissions. (Requires: Server Admin or Bot Manager/Owner)
*   `<code>/settings welcomemessages <action> [channel]</code>`: Manage welcome messages. Actions: enable, disable, status. (Requires: Manage Server or Bot Manager/Owner)
*   `<code>/settings logging <action> [channel]</code>`: Manage server activity logging. Actions: enable, disable, status. (Requires: Manage Server or Bot Manager/Owner)

## Setup

1.  Clone the repository.
2.  Install dependencies: `pip install -r requirements.txt`
3.  Create a `.env` file in the root directory with your `BOT_TOKEN`. Example:
    ```
    BOT_TOKEN=YOUR_DISCORD_BOT_TOKEN_HERE
    ```
4.  Ensure `items.csv` and `perks.csv` are present in the root directory.
5.  Run the bot: `python main.py`

For automatic updates, ensure `update_bot.ps1` (Windows) or `update_bot.sh` (Linux) is executable and correctly configured for your environment. The bot also needs a process manager (like PM2 or systemd) to restart it after an update.

## Important Links

*   View on GitHub
*   [Project Documentation](https://your-documentation-url-here) <!-- Or remove if README is the main doc -->
*   Official New World Site

---

<p align="center">
  <small>Crafted with Azoth for the New World community &copy; 2025. Ina's Bot is a fan project and not affiliated with Amazon Games.</small>
</p>
