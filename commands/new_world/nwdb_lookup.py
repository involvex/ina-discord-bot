import interactions
import sqlite3
import logging

# It's good practice to have a logger per module.
log = logging.getLogger(__name__)

# A helper function to query the database.
# This might live in a utils file, but for a self-contained example, it's here.
def search_item_in_db(item_name: str):
    """Searches for an item in the new_world_data.db and returns its details."""
    try:
        # Assuming the DB is in the root directory
        con = sqlite3.connect("new_world_data.db")
        cur = con.cursor()

        # Use a LIKE query for partial matches. The % are wildcards.
        # This is a basic example; your actual database schema might be different.
        res = cur.execute(
            "SELECT name, description, rarity, item_type FROM items WHERE name LIKE ? LIMIT 1",
            (f"%{item_name}%",)
        )
        item = res.fetchone()
        con.close()

        if item:
            # Return data in a structured way
            return {
                "name": item[0],
                "description": item[1],
                "rarity": item[2],
                "item_type": item[3]
            }
        return None
    except sqlite3.Error as e:
        log.error(f"Database error while searching for item '{item_name}': {e}")
        return None

class NWDBLookup(interactions.Extension):
    def __init__(self, bot: interactions.Client):
        self.bot = bot
        log.info("NWDBLookup Extension loaded.")

    @interactions.slash_command(
        name="nwdb",
        description="Look up items from New World Database.",
    )
    @interactions.slash_option(
        name="item_name",
        description="The name of the item to look up.",
        opt_type=interactions.OptionType.STRING,
        required=True,
        autocomplete=True
    )
    async def nwdb(self, ctx: interactions.SlashContext, item_name: str):
        await ctx.defer() # Acknowledge the command immediately

        item_data = search_item_in_db(item_name)

        if not item_data:
            await ctx.send(f"Sorry, I couldn't find any item matching `{item_name}`.", ephemeral=True)
            return

        # Create a nice embed for the response
        embed = interactions.Embed(
            title=f"📜 {item_data.get('name', 'N/A')}",
            description=item_data.get('description', 'No description available.'),
            color=interactions.Color.from_hex("#daa520") # Goldenrod color from your CSS
        )
        embed.add_field(name="Rarity", value=str(item_data.get('rarity', 'Unknown')), inline=True)
        embed.add_field(name="Item Type", value=item_data.get('item_type', 'Unknown'), inline=True)
        embed.set_footer(text="Data from New World Database")

        await ctx.send(embed=embed)

    @nwdb.autocomplete("item_name")
    async def item_autocomplete(self, ctx: interactions.AutocompleteContext):
        if not ctx.input_text:
            await ctx.send([])
            return

        try:
            con = sqlite3.connect("new_world_data.db")
            cur = con.cursor()
            res = cur.execute(
                "SELECT name FROM items WHERE name LIKE ? LIMIT 25",
                (f"%{ctx.input_text}%",)
            )
            choices = [interactions.SlashCommandChoice(name=row[0], value=row[0]) for row in res.fetchall()]
            con.close()
            await ctx.send(choices=choices)
        except sqlite3.Error as e:
            log.error(f"Autocomplete DB error: {e}")
            await ctx.send([])

# This is the crucial part that the loader looks for.
def setup(bot: interactions.Client):
    NWDBLookup(bot)