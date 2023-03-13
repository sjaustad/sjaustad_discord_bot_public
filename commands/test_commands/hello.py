import discord
from discord import app_commands
from discord.ext import commands

from utils.messages.user_input import UserInput
from utils.views.dropdown import DropdownMenu

class hello_command_cog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="hello")
    async def hello(self, interaction: discord.Interaction):
        menu_options = [
            discord.SelectOption(label='Red', description='Your favourite colour is red', emoji='🟥'),
            discord.SelectOption(label='Green', description='Your favourite colour is green', emoji='🟩'),
            discord.SelectOption(label='Blue', description='Your favourite colour is blue', emoji='🟦'),
        ]
        #dropdown_view = DropdownMenu()
        await interaction.response.defer(ephemeral=True)

        await DropdownMenu.display(interaction, menu_options, "Pick your favorite color...")
        DropdownMenu.ui.callback = callback

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(hello_command_cog(bot))

async def callback(self, interaction: discord.Interaction):
    await interaction.response.send_message(f'Your favourite colour is {self.values[0]}', ephemeral=True)
    if self.values[0] == "Red":
        menu_options = [
            discord.SelectOption(label='turd', description='Your favourite colour is red', emoji='🟥'),
            discord.SelectOption(label='blue', description='Your favourite colour is green', emoji='🟩'),
            discord.SelectOption(label='blurple', description='Your favourite colour is blue', emoji='🟦'),
        ]
        #dropdown_view = DropdownMenu()
        await DropdownMenu.display(interaction, menu_options, "Pick your favorite color...")
        
        DropdownMenu.ui.callback = callback2

async def callback2(self, interaction: discord.Interaction):
    await interaction.response.send_message(f'Your newest choice is {self.values[0]}', ephemeral=True)