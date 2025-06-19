import csv
import os
from typing import Dict, Optional
from config import PERKS_FILE # Import PERKS_FILE

def load_perks_from_csv(csv_filepath: str = PERKS_FILE) -> Dict[str, Dict[str, str]]:
    """Loads perk data from a CSV file into a dictionary.
    The keys of the main dictionary are lowercase perk names.
    The values are dictionaries representing the row data with original CSV header keys.
    """
    perks_data: Dict[str, Dict[str, str]] = {}
    
    # Construct the full path relative to this script's directory
    # This ensures it works correctly even if the main script is run from a different CWD
    dir_path = os.path.dirname(os.path.realpath(__file__))
    full_path = os.path.join(dir_path, csv_filepath)

    try:
        with open(full_path, mode='r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            
            if not reader.fieldnames:
                print(f"Warning: Perk CSV file '{full_path}' is empty or has no headers.")
                return perks_data
            
            # Determine the perk name column (case-insensitive)
            perk_name_column = None
            possible_name_columns = ['name', 'perkname', 'perk_name', 'title'] # Add more if needed
            
            for col_option in possible_name_columns:
                for actual_col in reader.fieldnames:
                    if actual_col.lower() == col_option:
                        perk_name_column = actual_col
                        break
                if perk_name_column:
                    break
            
            if not perk_name_column:
                # Fallback to trying 'name' if specific ones not found, or error if no 'name'
                if 'name' in reader.fieldnames: # Check original case 'name'
                    perk_name_column = 'name'
                elif 'Name' in reader.fieldnames: # Check 'Name'
                     perk_name_column = 'Name'
                else:
                    print(f"Error: No suitable perk name column found in '{full_path}'. Looked for {possible_name_columns} and 'name'/'Name'.")
                    return perks_data # Return empty if no name column

            for row in reader:
                perk_name_val = row.get(perk_name_column)
                if perk_name_val and perk_name_val.strip(): # Ensure perk name is not empty
                    perks_data[perk_name_val.lower()] = row # Store the original row dictionary
                # else:
                #     print(f"Warning: Row found with empty or missing perk name in '{full_path}': {row}")

    except FileNotFoundError:
        print(f"Error: The perk CSV file '{full_path}' was not found.")
        return {} 
    except Exception as e:
        print(f"An error occurred while reading the perk CSV file '{full_path}': {e}")
        return {} 
        
    return perks_data

if __name__ == '__main__':
    # Example usage for testing perks.py directly
    all_perks = load_perks_from_csv()
    if all_perks:
        print(f"Loaded {len(all_perks)} perks from '{PERKS_FILE}'.")
        # Print the first 2 perks for verification
        for i, (name, data) in enumerate(all_perks.items()):
            if i < 2:
                print(f"Perk: {name}")
                for key, value in data.items():
                    print(f"  {key}: {value}")
            else:
                break
    else:
        print(f"Failed to load perks from '{PERKS_FILE}'.")
