import csv
import io

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
csv_data = """
"Icon","Name","Item ID","Ingredients","Tradeskill","Source","Bookmark","In Stock","Price","Crafting Category","Crafting Group","Recipe Level","Can Craft","Yield Bonus","Tradskill XP","Standing XP","Station","Expansion","Bonus Chance","Cooldown Quantity","Cooldown Time","Additional Filter Text","Attribute Only Perk Item Slot Count","Base Gear Score","Base Tier","Bonus Item Chance Decrease","Bonus Item Chance Increase","Craft All","Crafting Fee","Disallow Bonuses To GS","Display Ingredients","First Craft Achievement Id","Game  Event  Validation","Game Event ID","Gear Score Bonus","Gear Score Reduction","Hidden By Achievement ID","Ingredient1","Ingredient2","Ingredient3","Ingredient4","Ingredient5","Ingredient6","Ingredient7","Is Procedural","Is Refining","Is Temporary","Max Perk Items Allowed","Output Qty","Perk Cost","Perk Items Bucket Push","Qty1","Qty2","Qty3","Qty4","Qty5","Qty6","Qty7","Recipe ID","Recipe Name Override","Recipe Tags","Required Achievement ID","Required World Tags","Skip Grant Items","Skip Grant Items Body","Skip Grant Items Desc","Skip Grant Items Title","Station Type1","Station Type2","Station Type3","Station Type4","Type1","Type2","Type3","Type4","Type5","Type6","Type7","Unlocked Achievement Blocks Recrafting","Unlocked Achievement ID","Use Crafting Tax","bKnown By Default","bListed By Default"
"","Artisan's Fire Staff","Artisan_FirestaffT52","TimberT53, IngotT53, LeatherT53, EssenceFireT1","Arcana","Arcana","0","","","Artisan Crafting","Fire Staves","250","true","","41669","40","Arcane Repository Tier 2","","0%","","","","0","700","5","","","false","449","","","FC_Artisan_FirestaffT5","true","Craft_ArcanaT52","","","","TimberT53","IngotT53","LeatherT53","EssenceFireT1","","","","false","false","false","0","1","0","","8","5","4","3","0","0","0","Artisan_FirestaffT5","Artisan_FirestaffT5_MasterName","Firestaff","","","false","","","","alchemy2","","","","Item","Item","Item","Item","","","","","","1","true","true"
"","Artisan's Life Staff","Artisan_LifestaffT52","TimberT53, IngotT53, LeatherT53, EssenceLifeT1","Arcana","Arcana","0","","","Artisan Crafting","Life Staves","250","true","","41669","40","Arcane Repository Tier 2","","0%","","","","0","700","5","","","false","449","","","FC_Artisan_LifestaffT5","true","Craft_ArcanaT52","","","","TimberT53","IngotT53","LeatherT53","EssenceLifeT1","","","","false","false","false","0","1","0","","8","5","4","3","0","0","0","Artisan_LifestaffT5","Artisan_LifestaffT5_MasterName","Lifestaff","","","false","","","","alchemy2","","","","Item","Item","Item","Item","","","","","","1","true","true"
"","Artisan's Ice Gauntlet","Artisan_IceGauntletT52","LeatherT53, ClothT53, IngotT53, EssenceWaterT1","Arcana","Arcana","0","","","Artisan Crafting","Ice Gauntlets","250","true","","41669","40","Arcane Repository Tier 2","","0%","","","","0","700","5","","","false","449","","","FC_Artisan_IceGauntletT5","true","Craft_ArcanaT52","","","","LeatherT53","ClothT53","IngotT53","EssenceWaterT1","","","","false","false","false","0","1","0","","8","5","4","3","0","0","0","Artisan_IceGauntletT5","Artisan_IceGauntletT5_MasterName","IceGauntlet","","","false","","","","alchemy2","","","","Item","Item","Item","Item","","","","","","1","true","true"
"","Artisan's Void Gauntlet","Artisan_VoidGauntletT52","LeatherT53, ClothT53, IngotT53, EssenceDeathT1","Arcana","Arcana","0","","","Artisan Crafting","Void Gauntlets","250","true","","41669","40","Arcane Repository Tier 2","","0%","","","","0","700","5","","","false","449","","","FC_Artisan_VoidGauntletT5","true","Craft_ArcanaT52","","","","LeatherT53","ClothT53","IngotT53","EssenceDeathT1","","","","false","false","false","0","1","0","","8","5","4","3","0","0","0","Artisan_VoidGauntletT5","Artisan_VoidGauntletT5_MasterName","VoidGauntlet","","","false","","","","alchemy2","","","","Item","Item","Item","Item","","","","","","1","true","true"
"","Artisan Flail","Artisan_FlailT52","IngotT53, LeatherT53, ClothT53, PearlT1","Arcana","Arcana","0","","","Artisan Crafting","Flail","250","true","","35419","34","Arcane Repository Tier 2","Expansion2023","0%","","","","0","700","5","","","false","449","","","FC_Artisan_FlailT5","false","Craft_ArcanaT52","","","","IngotT53","LeatherT53","ClothT53","PearlT1","","","","false","false","false","0","1","0","","8","2","4","3","0","0","0","Artisan_FlailT5","Artisan_FlailT5_MasterName","Flail","","","false","","","","alchemy2","","","","Item","Item","Item","Item","","","","","","1","true","true"
"","Iron Fire Staff","2hElementalStaff_FireT2","TimberT2, Metal, Leather, ArcanaFire","Arcana","Arcana","0","","75","Magical Weapons","Fire Staves","0","true","","414","46","Arcane Repository Tier 2","","0%","","","","0","200","2","","","false","25","","","FC_Procedural_StaffFireT2","true","Craft_ArcanaT2","5,10,15,20,25","-5,-10,-15,-20,-25","","TimberT2","Metal","Leather","ArcanaFire","","","","true","false","false","0","1","15","","8","5","4","6","0","0","0","Procedural_StaffFireT2","Procedural_StaffFireT2","StaffFire","","","false","","","","alchemy2","","","","Category_Only","Category_Only","Category_Only","Category_Only","","","","","","1","true","true"
"","Steel Fire Staff","2hElementalStaff_FireT3","TimberT3, Metal, Leather, ArcanaFire","Arcana","Arcana","0","","132.5","Magical Weapons","Fire Staves","50","true","","1380","46","Arcane Repository Tier 2","","0%","","","","0","300","3","","","false","75","","","FC_Procedural_StaffFireT3","true","Craft_ArcanaT3","5,10,15,20,25","-5,-10,-15,-20,-25","","TimberT3","Metal","Leather","ArcanaFire","","","","true","false","false","0","1","15","","8","5","4","6","0","0","0","Procedural_StaffFireT3","Procedural_StaffFireT3","StaffFire","","","false","","","","alchemy2","","","","Category_Only","Category_Only","Category_Only","Category_Only","","","","","","1","true","true"
"""

parsed_recipes = parse_recipes(csv_data)
formatted_output = format_recipes(parsed_recipes)

if __name__ == "__main__":
    print(formatted_output)