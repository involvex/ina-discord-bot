"""
Store crafting recipes for New World items
"""

RECIPES = {
    "iron ingot": {
        "station": "Smelter",
        "skill": "Smelting",
        "skill_level": 0,
        "tier": 2,
        "ingredients": [
            {"item": "Iron Ore", "quantity": 4}
        ]
    },
    "steel ingot": {
        "station": "Smelter",
        "skill": "Smelting",
        "skill_level": 50,
        "tier": 3,
        "ingredients": [
            {"item": "Iron Ingot", "quantity": 3},
            {"item": "Charcoal", "quantity": 1},
            {"item": "Flux", "quantity": 1}
        ]
    },
    "starmetal ingot": {
        "station": "Smelter",
        "skill": "Smelting",
        "skill_level": 100,
        "tier": 4,
        "ingredients": [
            {"item": "Starmetal Ore", "quantity": 6},
            {"item": "Steel Ingot", "quantity": 2},
            {"item": "Charcoal", "quantity": 1},
            {"item": "Flux", "quantity": 1}
        ]
    },
    "orichalcum ingot": {
        "station": "Smelter",
        "skill": "Smelting",
        "skill_level": 150,
        "tier": 5,
        "ingredients": [
            {"item": "Orichalcum Ore", "quantity": 8},
            {"item": "Starmetal Ingot", "quantity": 2},
            {"item": "Charcoal", "quantity": 1},
            {"item": "Flux", "quantity": 1}
        ]
    },
    "infused health potion": {
        "station": "Arcane Repository",
        "skill": "Arcana",
        "skill_level": 100,
        "tier": 4,
        "ingredients": [
            {"item": "Water", "quantity": 1},
            {"item": "Life Mote", "quantity": 2},
            {"item": "Azoth Water", "quantity": 1},
            {"item": "Medicinal Reagent", "quantity": 1}
        ]
    },
    "powerful health serum": {
        "station": "Arcane Repository",
        "skill": "Arcana",
        "skill_level": 150,
        "tier": 5,
        "ingredients": [
            {"item": "Strong Health Potion", "quantity": 1},
            {"item": "Life Quintessence", "quantity": 1},
            {"item": "Azoth Water", "quantity": 2},
            {"item": "Medicinal Reagent", "quantity": 2}
        ]
    }
}

def get_recipe(item_name: str) -> dict:
    """
    Get the crafting recipe for an item
    Returns None if no recipe exists
    """
    return RECIPES.get(item_name.lower())

def format_recipe(recipe: dict) -> str:
    """
    Format a recipe into a readable string
    """
    if not recipe:
        return None
        
    output = []
    output.append(f"Crafted at: {recipe['station']} ({recipe['skill']} {recipe['skill_level']})")
    output.append(f"Tier: {recipe['tier']}")
    output.append("\nIngredients:")
    
    for ingredient in recipe['ingredients']:
        output.append(f"• {ingredient['quantity']} {ingredient['item']}")
        
    return "\n".join(output)

def calculate_crafting_materials(item_name: str, quantity: int = 1, include_intermediate: bool = False) -> dict:
    """
    Calculate total raw materials needed to craft an item.
    
    Args:
        item_name: Name of the item to craft
        quantity: Number of items to craft
        include_intermediate: If True, includes intermediate crafted items in the output
    
    Returns:
        Dictionary with material names as keys and total quantities as values.
        Returns None if recipe doesn't exist.
    """
    recipe = get_recipe(item_name)
    if not recipe:
        return None
        
    def _calculate_materials(recipe_name: str, amount: int, materials: dict) -> None:
        recipe = get_recipe(recipe_name)
        if not recipe:
            # This is a raw material
            materials[recipe_name] = materials.get(recipe_name, 0) + amount
            return
            
        # Process each ingredient in the recipe
        for ingredient in recipe['ingredients']:
            ing_name = ingredient['item'].lower()
            ing_quantity = ingredient['quantity'] * amount
            
            sub_recipe = get_recipe(ing_name)
            if sub_recipe:
                # This is an intermediate crafted item
                if include_intermediate:
                    materials[ing_name] = materials.get(ing_name, 0) + ing_quantity
                _calculate_materials(ing_name, ing_quantity, materials)
            else:
                # This is a raw material
                materials[ing_name] = materials.get(ing_name, 0) + ing_quantity
    
    materials = {}
    _calculate_materials(item_name.lower(), quantity, materials)
    return materials