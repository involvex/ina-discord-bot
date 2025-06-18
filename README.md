# Ina's New World Bot

Your friendly Discord companion for all things Aeternum! Ina helps you look up items, perks, calculate crafting costs, manage builds, and much more.

## Features

*   **Item & Perk Lookup:** Quickly find details about New World items and perks.
*   **Crafting Assistance:** Calculate materials for crafts and view full recipe breakdowns.
*   **Build Management:** Save and share your favorite `nw-buddy.de` builds.
*   **Server Utilities:** Optional welcome messages for new members and server activity logging.
*   **Fun Commands:** Includes `/petpet` and more!
*   **Bot Management:** Tools for bot owners and administrators to manage the bot.
*   **Automatic Updates:** Ina can check for and apply updates to herself (requires setup).

## Commands

Here's a list of available commands. Use `/help [command_name]` in Discord for more details on a specific command.

### General Commands
*   **/ping**: Check if the bot is online.
*   **/help [command_name]**: Show available commands or help for a specific command.
*   **/petpet &lt;user&gt;**: Give a New World petting ritual to a user!
*   **/calculate &lt;expression&gt;**: Perform a calculation with New World magic!
*   **/about**: Show information about Ina's New World Bot.

### New World Specific Commands
*   **/nwdb &lt;item_name&gt;**: Look up items from New World Database.
*   **/perk &lt;perk_name&gt;**: Look up information about a specific New World perk.
*   **/recipe &lt;item_name&gt;**: Show the full recipe breakdown for a craftable item.
*   **/calculate_craft &lt;item_name&gt; [amount]**: Calculate resources needed to craft an item, including intermediates.

### Build Management
*   **/build add &lt;link&gt; &lt;name&gt; [keyperks]**: Add a build from nw-buddy.de.
*   **/build list**: Show a list of saved builds.
*   **/build remove &lt;name&gt;**: Remove a saved build. (Requires: Manage Server or Bot Manager)

### Management & Settings (Require Permissions)
*   **/manage update**: Pulls updates from GitHub and restarts the bot. (Requires: Bot Owner)
*   **/manage restart**: Shuts down the bot for manual restart. (Requires: Bot Owner/Manager)
*   **/settings permit &lt;user&gt;**: Grants a user bot management permissions. (Requires: Server Admin or Bot Owner)
*   **/settings unpermit &lt;user&gt;**: Revokes a user's bot management permissions. (Requires: Server Admin or Bot Owner)
*   **/settings listmanagers**: Lists users with bot management permissions. (Requires: Server Admin or Bot Manager/Owner)
*   **/settings welcomemessages &lt;action&gt; [channel]**: Manage welcome messages. Actions: enable, disable, status. (Requires: Manage Server or Bot Manager/Owner)
*   **/settings logging &lt;action&gt; [channel]**: Manage server activity logging. Actions: enable, disable, status. (Requires: Manage Server or Bot Manager/Owner)

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

## Contributing
Contributions are welcome! Please feel free to submit a pull request or open an issue.

*(You can add more sections like License, Acknowledgements, etc.)*
