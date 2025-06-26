import logging
import json
from interactions import Extension, slash_command, slash_option, OptionType, SlashContext, Embed, EmbedField
from recipes import get_recipe # Assuming this is how it's imported

logger = logging.getLogger(__name__)

class NewWorldCrafting(Extension):
    def __init__(self, bot):
        self.bot = bot

    @slash_command(name="recipe", description="Shows the crafting recipe for an item.")
    @slash_option(
        name="item_name",
        description="The name of the item to look up.",
        opt_type=OptionType.STRING,
        required=True
    )
    async def recipe(self, ctx: SlashContext, item_name: str):
        await ctx.defer() # Defer the response as lookup might take time

        recipe_data = await get_recipe(item_name)

        if not recipe_data:
            await ctx.send(f"Sorry, I couldn't find a recipe for '{item_name}'.")
            return

        embed = Embed(
            title=f"Crafting Recipe for {recipe_data.get('output_item_name', item_name)}",
            color=0x00ff00 # Green color
        )

        # Safely get ingredients. get_recipe should return a list, but add a check for robustness.
        ingredients = recipe_data.get('ingredients', [])
        
        # Ensure ingredients is a list (it should be from get_recipe's json.loads)
        if isinstance(ingredients, str):
            try:
                ingredients = json.loads(ingredients)
            except json.JSONDecodeError:
                logger.error(f"Failed to decode ingredients JSON for {item_name}: {ingredients}")
                ingredients = [] # Fallback to empty list on decode error

        # Format ingredients for display, providing a fallback string if empty
        if ingredients:
            ingredients_str = "\n".join([f"{ing.get('quantity', 1)}x {ing.get('item', 'Unknown Item')}" for ing in ingredients])
        else:
            ingredients_str = "No ingredients required." # This is the crucial fix for the "BASE_TYPE_REQUIRED" error

        embed.add_field(name="Ingredients", value=ingredients_str, inline=False)

        # Add other fields, ensuring they also have non-empty fallback values
        # Assuming 'station', 'skill', 'skill_level', 'tier' are also present in recipe_data
        embed.add_field(name="Crafting Station", value=recipe_data.get('station', 'Not specified'), inline=True)
        
        skill_info = []
        if recipe_data.get('skill'):
            skill_info.append(recipe_data['skill'])
        if recipe_data.get('skill_level'):
            skill_info.append(f"(Level {recipe_data['skill_level']})")
        embed.add_field(name="Skill Required", value=" ".join(skill_info) or "Not specified", inline=True)

        embed.add_field(name="Tier", value=str(recipe_data.get('tier', 'Not specified')), inline=True)

        await ctx.send(embeds=embed)

def setup(bot):
    NewWorldCrafting(bot)