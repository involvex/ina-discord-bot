<p align="center">
  <a href="https://github.com/involvex/ina-discord-bot">
    <img src="https://raw.githubusercontent.com/involvex/ina-discord-bot/main/docs/src/images/logo.png" alt="Ina's New World Bot Logo" width="150"/>
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

---

## ✨ Key Features - Master the Island's Depths!

* ⚔️ **Deep Dive Database:** Instantly access detailed information on New World items, perks, and recipes, leveraging data from `nwdb.info`. For example, use `/nwdb`, `/perk`, or `/recipe`.
* 🔨 **Strategic Crafting:** Calculate materials for crafts, view full recipe breakdowns, and determine exact costs for your crafting endeavors. Try `/calculate_craft` or `/recipe`.
* 🛡️ **Build Management:** Save, share, and manage your favorite New World builds directly from `nw-buddy.de`. Use `/build add` or `/build list`.
* 👑 **Server Enhancements:** Enhance your server with optional welcome messages for new members and activity logging, making your guild hall truly grand.
* 🌟 **Aeternum Fun:** Engage with fun commands, including the legendary `/petpet` ritual and more! Discover hidden delights.
* 📜 **Bot Administration:** Tools for bot owners and administrators to manage the bot, including permissions and updates. Keep order in your domain.
* 🔄 **Automatic Updates:** Configure Ina to check for and apply updates to herself (requires specific server-side setup), ensuring you always have the latest wisdom.
* 📈 **Always Evolving:** Regularly updated with new features, improvements, and the latest New World game data. Aeternum's secrets are ever unfolding, and so is Ina!

---

## Commands - Your Toolkit for Aeternum!

Here's a list of available commands to aid your journey. Use `/help [command_name]` in Discord for more details on a specific command.

### General Commands
* `/ping`: Check if the bot is online – a quick whisper across the realms.
* `/help [command_name]`: Show available commands or help for a specific command – consult the ancient texts.
* `/petpet <user>`: Give a New World petting ritual to a user! Show your appreciation.
* `/calculate <expression>`: Perform a calculation with New World magic! Unravel complex equations.
* `/about`: Show information about Ina's New World Bot – learn about your companion.

### New World Specific Commands
* `/nwdb <item_name>`: Look up items from New World Database – identify relics and resources.
* `/perk <perk_name>`: Look up information about a specific New World perk – master your combat advantages.
* `/recipe <item_name>`: Show the full recipe breakdown for a craftable item – unlock the secrets of creation.
* `/calculate_craft <item_name> [amount]`: Calculate resources needed to craft an item, including intermediates – plan your grand designs.

### Build Management
* `/build add <link> <name> [keyperks]`: Add a build from nw-buddy.de.
* `/build list`: Show a list of saved builds.
* `/build remove <name>`: Remove a saved build. (Requires: Manage Server or Bot Manager)

### Management & Settings (Require Permissions)
* `/manage update`: Pulls updates from GitHub and restarts the bot. (Requires: Bot Owner)
* `/manage restart`: Shuts down the bot for manual restart. (Requires: Bot Owner/Manager)
* `/settings permit <user>`: Grants a user bot management permissions. (Requires: Server Admin or Bot Owner)
* `/settings unpermit <user>`: Revokes a user's bot management permissions. (Requires: Server Admin or Bot Owner)
* `/settings listmanagers`: Lists users with bot management permissions. (Requires: Server Admin or Bot Manager/Owner)
* `/settings welcomemessages <action> [channel]`: Manage welcome messages. Actions: `enable`, `disable`, `status`. (Requires: Manage Server or Bot Manager/Owner)
* `/settings logging <action> [channel]`: Manage server activity logging. Actions: `enable`, `disable`, `status`. (Requires: Manage Server or Bot Manager/Owner)

---

## Setup - Embark on Your Journey!

1.  Clone the repository.
2.  Install dependencies: `pip install -r requirements.txt`
3.  Create a `.env` file in the root directory with your `BOT_TOKEN`. Example:
    ```
    BOT_TOKEN=YOUR_DISCORD_BOT_TOKEN_HERE
    ```
4.  Ensure `items.csv` and `perks.csv` are present in the root directory.
5.  Run the bot: `python main.py`

For automatic updates, ensure `update_bot.ps1` (Windows) or `update_bot.sh` (Linux) is executable and correctly configured for your environment. The bot also needs a process manager (like PM2 or systemd) to restart it after an update.

---

## Important Links - Paths to Knowledge

* 🔗 [View on GitHub](https://github.com/involvex/ina-discord-bot)
* 📖 [Project Documentation](https://involvex.github.io/ina-discord-bot/)
* 🎮 [Official New World Site](https://www.newworld.com/)
* 🌐 [New World Database (nwdb.info)](https://nwdb.info/)

---

<p align="center">
  <small>Created by Ina (Furnishing 250) and AI (Logging level 5)</small><br>
  <small>Crafted with Azoth for the New World community &copy; 2025. Ina's Bot is a fan project and not affiliated with Amazon Games.</small>
</p>
