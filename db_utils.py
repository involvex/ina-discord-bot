import sqlite3
import os
import logging
import time
import platform
import asyncio
import aiosqlite # Use the async library
from config import DB_NAME # Import DB_NAME

async def find_item_in_db(item_name_query: str, exact_match: bool = False):
    if not os.path.exists(DB_NAME): # Use imported DB_NAME
        logging.error(f"find_item_in_db: Database {DB_NAME} not found.")
        return [] 

    results = []
    try:
        start_time = time.perf_counter() # Added timing
        async with aiosqlite.connect(DB_NAME) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.cursor() as cursor:
                if exact_match:
                    query = "SELECT * FROM items WHERE lower(Name) = ? LIMIT 25"
                    logging.info(f"Executing exact match query: {query} with item_name_query='{item_name_query}'")
                    await cursor.execute(query, (item_name_query.lower(),))
                else:
                    query = "SELECT * FROM items WHERE lower(Name) LIKE ? LIMIT 25"
                    logging.info(f"Executing LIKE query: {query} with item_name_query='{item_name_query}'")
                    await cursor.execute(query, ('%' + item_name_query.lower() + '%',))
                items = await cursor.fetchall()
                logging.info(f"Query returned {len(items)} results.")
                results = [dict(row) for row in items]
    except aiosqlite.Error as e:
        end_time = time.perf_counter()
        logging.info(f"find_item_in_db took {end_time - start_time:.4f} seconds")
        logging.error(f"SQLite error in find_item_in_db: {e}", exc_info=True)
        return [] 
    return results

async def find_perk_in_db(perk_name_query: str, exact_match: bool = False, _attempted_update: bool = False):
    if not os.path.exists(DB_NAME): # Use imported DB_NAME
        logging.error(f"find_perk_in_db: Database {DB_NAME} not found.")
        return []
    results = []
    try:
        async with aiosqlite.connect(DB_NAME) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.cursor() as cursor:
                # Use lower() to make the search case-insensitive and utilize the lowercase index
                if exact_match:
                    await cursor.execute("SELECT * FROM perks WHERE lower(name) = ? LIMIT 25", (perk_name_query.lower(),))
                else:
                    await cursor.execute("SELECT * FROM perks WHERE lower(name) LIKE ? LIMIT 25", ('%' + perk_name_query.lower() + '%',))
                perks_data = await cursor.fetchall()
                results = [dict(row) for row in perks_data]
    except aiosqlite.Error as e:
        logging.error(f"SQLite error in find_perk_in_db: {e}", exc_info=True)
        return []

    if not results and not _attempted_update: # Only attempt update if not found AND not already attempted
        logging.info(f"No perk '{perk_name_query}' found in database, attempting to auto-run perk data update.")
        current_os = platform.system().lower()
        script_dir = os.path.dirname(os.path.abspath(__file__)) # Assumes db_utils.py is in the root
        
        script_to_run = None
        run_command = []

        if "windows" in current_os:
            script_to_run = os.path.join(script_dir, "update_perks.ps1")
            run_command = ["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", script_to_run]
        elif "linux" in current_os:
            script_to_run = os.path.join(script_dir, "update_perks.sh")
            run_command = ["/bin/bash", script_to_run]
        else:
            logging.warning(f"Unsupported OS ({current_os}) for running update_perks script. Manual intervention needed")
            return results

        if script_to_run and os.path.exists(script_to_run):
            try:
                logging.info(f"Executing update script: {run_command}")
                process = await asyncio.create_subprocess_exec(
                    *run_command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()

                if stdout:
                    logging.info(f"Update script stdout:\n{stdout.decode(errors='ignore')}")
                if stderr:
                    logging.warning(f"Update script stderr:\n{stderr.decode(errors='ignore')}")
                
                if process.returncode != 0:
                    logging.error(f"Update script failed with exit code {process.returncode}.")
                else:
                    logging.info("Update script executed successfully.")
            except Exception as e:
                logging.error(f"Error running update script {script_to_run}: {e}", exc_info=True)
        else:
            logging.error(f"Update script not found or not specified: {script_to_run}")

        results = await find_perk_in_db(perk_name_query, exact_match=exact_match, _attempted_update=True) # Recursive call with flag
        if results:
            logging.info(f"Automatic perk update succeeded. '{perk_name_query}' found in updated data.")
    return results