import discord, traceback
from discord import app_commands
from discord.ext import commands

from utils.views.button_menu import InteractionMenu

class Menu_cog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="app_command_menu_template", description="<description>")
    async def menu(self, interaction: discord.Interaction):
        options = ['pie','cookies','ice cream','cake']

        embed = discord.Embed(title="This is a dessert menu!")

        ## instantiate menu class
        menu = InteractionMenu(self.bot)
        ## define the call back for the custom_button
        ## see below for async callback
        menu.custom_button.callback = callback
        ## Generate the menu view with the buttons
        menu_view = await menu.generate_view(options, interaction=interaction)
        ## Send the menu message
        await interaction.response.send_message(view=menu_view, embed=embed, ephemeral=True)


        ## if you are not sending an interaction, but rather a regular message and you want
        ## to be able to edit the original message inside the callback, you will need to add
        ## the message to each button with this method.
        #menu.allow_original_menu_updates(menu_view, menu_message)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Menu_cog(bot))


async def callback(self, interaction: discord.Interaction) -> None:

    ## if they choose cancel
    if self.value.lower() == "cancel":
        return await self.menu_message.edit_original_response(content=f"Cancelled menu.", view=None, embed=None)
    
    ## console log choice
    print(f"You chose {self.value}!")
    ## create new embed
    new_embed = discord.Embed(title=f"You selected {self.value} at menu index {self.index}")
    ## remove the options and send new embed to original message
    await self.menu_message.edit_original_response(view=None, embed=new_embed)

    ## if the original message sent is not ephemeral (user only) you can delete it, otherwise you cannot
    #await self.menu_message.delete_original_response()