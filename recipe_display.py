import csv
import io
import requests # Import the requests library

def parse_recipes(csv_data):
    """
    Parses CSV data containing crafting recipes and extracts relevant information.

    Args:
        csv_data (str): A string containing CSV data of crafting recipes.

    Returns:
        list: A list of dictionaries, where each dictionary represents a recipe
              with 'Name' and 'Ingredients' (a list of {item: qty} dictionaries).
    """
    recipes = []
    csvfile = io.StringIO(csv_data)
    reader = csv.DictReader(csvfile)

    for row in reader:
        recipe_name = row.get("Name")
        if not recipe_name:
            continue

        ingredients = []
        for i in range(1, 8): # Iterate through Ingredient1 to Ingredient7
            ingredient_key = f"Ingredient{i}"
            qty_key = f"Qty{i}"

            ingredient_name = row.get(ingredient_key)
            qty_str = row.get(qty_key)

            if ingredient_name and qty_str:
                try:
                    qty = int(qty_str)
                    if qty > 0: # Only add ingredients with positive quantities
                        ingredients.append({"item": ingredient_name, "qty": qty})
                except ValueError:
                    # Handle cases where Qty is not a valid integer (e.g., empty string, non-numeric)
                    pass
        
        # Only add recipes that have at least one ingredient
        if ingredients:
            recipes.append({
                "Name": recipe_name,
                "Ingredients": ingredients
            })
    return recipes

def format_recipes(recipes):
    """
    Formats a list of parsed recipes into a human-readable string.

    Args:
        recipes (list): A list of dictionaries, as returned by parse_recipes.

    Returns:
        str: A formatted string displaying each recipe.
    """
    formatted_output = []
    for recipe in recipes:
        formatted_output.append(f"Recipe: {recipe['Name']}")
        formatted_output.append("  Ingredients:")
        if not recipe['Ingredients']:
            formatted_output.append("    (No specific ingredients listed or quantities are zero)")
        else:
            for ingredient in recipe['Ingredients']:
                formatted_output.append(f"    - {ingredient['item']}: {ingredient['qty']}")
        formatted_output.append("") # Add a blank line for separation
    return "\n".join(formatted_output)

# Your provided CSV data
# Use the raw content URL for the CSV file on GitHub
csv_file_path = 'https://raw.githubusercontent.com/involvex/ina-discord-bot/98d8c5b93799ac7d75c54a1543187a6a5a938e94/craftingsrecipe.csv'

if __name__ == "__main__":
    try:
        # Use requests to fetch the content from the URL
        response = requests.get(csv_file_path)
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
        csv_data = response.text
        
        parsed_recipes = parse_recipes(csv_data)
        formatted_output = format_recipes(parsed_recipes)
        print(formatted_output)
    except requests.exceptions.RequestException as e:
        # Catch any request-related errors (e.g., network issues, invalid URL, HTTP errors)
        print(f"Error fetching CSV from URL: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")