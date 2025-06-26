from interactions import slash_command, SlashContext, Embed, Color, OptionType, slash_option
import logging

# Assuming get_item is available from getitems.py or items.py
# Adjust this import path if your get_item function is located elsewhere
from getitems import get_item

logger = logging.getLogger(__name__)

@slash_command(
    name="nwdb",
    description="Look up items from New World Database.",
    dm_permission=True # This makes the command available in DMs
)
@slash_option(
    name="item_name",
    description="The name of the item to look up (e.g., 'Pristine Gleamite').",
    type=OptionType.STRING,
    required=True
)
async def nwdb_command(ctx: SlashContext, item_name: str):
    """
    Looks up an item in the New World Database and displays its information.
    """
    await ctx.defer() # Acknowledge the command immediately

    logger.info(f"Received /nwdb command from {ctx.author.id} for item: {item_name}")
    item_data = get_item(item_name)

    if not item_data:
        await ctx.send(f"Sorry, I couldn't find any item matching '{item_name}' in the database.")
        logger.info(f"Item '{item_name}' not found.")
        return

    # Construct the embed
    embed = Embed(
        title=item_data.get('Name', 'Unknown Item'),
        description=item_data.get('Description', 'No description available.'),
        color=Color.from_rgb(212, 175, 55) # A nice gold color, reminiscent of New World
    )

    # Add fields from the item data
    embed.add_field(name="Rarity", value=item_data.get('Rarity', 'Unknown'), inline=True)
    embed.add_field(name="Type", value=item_data.get('Item_Type_Name', 'Unknown'), inline=True)
    embed.add_field(name="Item ID", value=item_data.get('Item_ID', 'N/A'), inline=True)

    # Set the image (icon) if available
    if item_data.get('Icon_URL'):
        embed.set_thumbnail(url=item_data['Icon_URL'])

    await ctx.send(embeds=[embed])
    logger.info(f"Successfully sent info for item '{item_name}'.")