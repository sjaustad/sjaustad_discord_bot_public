import discord
from discord import app_commands
from discord.ext import commands

from utils.messages.user_input import UserInput

class example_cog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="text_response")
    async def hello(self, interaction: discord.Interaction):
        """Says hello!"""
        input = UserInput(self.bot)
        response = await input.get_text_response(user=interaction.user,channel=interaction.channel,embed=discord.Embed(title="How are you? Please type below."), timeout=10, interaction=interaction)
        #await interaction.response.send_message(f'Hi, {interaction.user.mention}')
        if response['user_message']:
            print(response)
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(example_cog(bot))