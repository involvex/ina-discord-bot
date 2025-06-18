import os
import sys
from interactions import Client
from dotenv import load_dotenv

load_dotenv() # Ensure .env is loaded before accessing BOT_TOKEN

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    print("Error: BOT_TOKEN not found in .env file. Please make sure it is set.", file=sys.stderr)
    sys.exit(1)

bot = Client(token=BOT_TOKEN)