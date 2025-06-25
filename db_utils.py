import sqlite3
import os
import logging
import time
import platform
import asyncio # Added for asyncio.create_subprocess_exec
from config import DB_NAME # Import DB_NAME


_db_connection = None

def get_db_connection():
    global _db_connection
    if not os.path.exists(DB_NAME): # Use imported DB_NAME
        logging.error(f"get_db_connection: Database '{DB_NAME}' not found when attempting to connect. Data-dependent features will fail.")
        return None
    if _db_connection is None:
        logging.info(f"Establishing new DB connection to {DB_NAME}")
    else:
        logging.debug(f"Reusing existing DB connection to {DB_NAME}")
    if _db_connection is None:
        _db_connection = sqlite3.connect(DB_NAME) # Use imported DB_NAME
        _db_connection.row_factory = sqlite3.Row # Access columns by name
    return _db_connection
 
async def find_item_in_db(item_name_query: str, exact_match: bool = False): # db_name_param removed
    if not os.path.exists(DB_NAME): # Use imported DB_NAME
        logging.error(f"find_item_in_db: Database {DB_NAME} not found.")
        return [] 

    conn = get_db_connection()
    results = []
    try:
        start_time = time.perf_counter() # Added timing
        cursor = conn.cursor()
        # Use lower() to make the search case-insensitive and utilize the lowercase index
        if exact_match:
             cursor.execute("SELECT * FROM items WHERE lower(Name) = ? LIMIT 25", (item_name_query.lower(),))
        else:
            cursor.execute("SELECT * FROM items WHERE lower(Name) LIKE ? LIMIT 25", ('%' + item_name_query.lower() + '%',))
        items = cursor.fetchall()
        results = [dict(row) for row in items]
    except sqlite3.Error as e:
        end_time = time.perf_counter()
        logging.info(f"find_item_in_db took {end_time - start_time:.4f} seconds")
        logging.error(f"SQLite error in find_item_in_db: {e}", exc_info=True)
        return [] 
    return results # Move return outside try/finally, as connection is global

async def find_perk_in_db(perk_name_query: str, exact_match: bool = False, _attempted_update: bool = False): # db_name_param removed
    if not os.path.exists(DB_NAME): # Use imported DB_NAME
        logging.error(f"find_perk_in_db: Database {DB_NAME} not found.")
        return []
    conn = get_db_connection()
    results = []
    try:
        cursor = conn.cursor()
        # Use lower() to make the search case-insensitive and utilize the lowercase index
        if exact_match:
            cursor.execute("SELECT * FROM perks WHERE lower(name) = ? LIMIT 25", (perk_name_query.lower(),))
        else:
            cursor.execute("SELECT * FROM perks WHERE lower(name) LIKE ? LIMIT 25", ('%' + perk_name_query.lower() + '%',))
        perks_data = cursor.fetchall()
        results = [dict(row) for row in perks_data]
    except sqlite3.Error as e:
        logging.error(f"SQLite error in find_perk_in_db: {e}", exc_info=True)
        return []
    finally:
        pass # Connection is managed globally

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
                logging.info(f"Executing update script: {' '.join(run_command)}")
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