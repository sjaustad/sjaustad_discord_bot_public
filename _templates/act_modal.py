import discord, traceback
from discord import app_commands
from discord.ext import commands
from datetime import datetime

from utils.database.calls.users import Users

from settings.server_settings import settings
settings = settings()
## Modal Information:
## Modals cannot be chained with interactions. If an interaction has been responded to, you cannot send a modal to it.
## You must make a new interaction for every modal. This can be done by creating a menu and having the user click a button.

## Modals require an interaction, a modal class (discord.ui.Modal) and an on_submit method for the modal

class ModalCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.users_db=Users(bot.redis)

    @app_commands.command(name="modal_example", description="Opens a modal form as the interaction")
    async def command(self, interaction: discord.Interaction):
        ## any arbitrary amount of variables can be passed to the modal, such as a database instance
        await interaction.response.send_modal(modal_example(self.bot, self.users_db))
        ## If you put code below this after sending the modal it will execute right when the modal is sent and before
        ## the user has had a chance to respond. All user input that needs to be processed needs to be inside the
        ## 'on_submit' function in the modal.
    
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ModalCog(bot))


class modal_example(discord.ui.Modal, title="Modal Title"):
    def __init__(self, bot, users_db):
        super().__init__()
        self.bot = bot
        self.users_db = users_db
    
    text_field_1 = discord.ui.TextInput(
        label='How can we improve the bot?',
        placeholder="Nothing, it's perfect",
    )    
    text_field_2 = discord.ui.TextInput(
        label='Additional comments',
        style=discord.TextStyle.long,
        placeholder="Placeholder can go here",
        required=False,
        max_length=600,
        default="A default value can also be set here"
    )
    

    async def on_submit(self, interaction: discord.Interaction):
        pass
        ## now you can do anything you would like with the variables passed to __init__ when creating the modal
        ## e.g. self.users_db.get_attribute(interaction.user.id, "some_attribute")
        ## access variables:
        self.text_field_1.value
        self.text_field_2.value

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        ## If you are too lazy to keep track of whether the interaction was definitively responded to:
        try:
            await interaction.response.send_message('Oops this is embarassing! Something went wrong. Contact bot owner.', ephemeral=True)
        except discord.errors.InteractionResponded:
            await interaction.followup.send(content='Oops this is embarassing! Something went wrong. Contact bot owner.', ephemeral=True)
        # Make sure we know what the error actually is
        traceback.print_tb(error.__traceback__)