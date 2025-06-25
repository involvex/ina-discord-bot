#!/bin/bash

# SYNOPSIS
# This script is a wrapper to update the bot's code and then start the bot.
# It assumes it is located in the root directory of your bot's Git repository.
#
# DESCRIPTION
#   1. Navigates to the script's directory.
#   2. Executes 'update_bot.sh' to fetch the latest code and install dependencies.
#   3. Starts the bot by running 'main.py' using the appropriate Python interpreter
#      (preferably from the virtual environment activated by 'update_bot.sh').
#
# NOTES
#   - Ensure 'update_bot.sh' is executable (chmod +x update_bot.sh).
#   - This script should be placed in the same directory as 'update_bot.sh' and 'main.py'.

# Exit immediately if any command fails.
set -e

echo "==================================="
echo "Ina's New World Bot - Wrapper Script"
echo "==================================="
echo ""

# Navigate to the script's directory (which should be the bot's root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || { echo "ERROR: Failed to navigate to bot directory $SCRIPT_DIR." >&2; exit 1; }
echo "INFO: Operating in directory: $(pwd)"
echo ""

# --- Step 1: Run the update script ---
echo "INFO: Running the bot update script (./update_bot.sh)..."
./update_bot.sh
echo "INFO: Bot update script completed."
echo ""

# --- Step 2: Start the bot ---
# The update_bot.sh script handles starting main.py with the correct venv.
# This wrapper's job is just to run the update script.
# The update_bot.sh script will then start the bot.


echo "INFO: Bot process started. This script will now exit."
