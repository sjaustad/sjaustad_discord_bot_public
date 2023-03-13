import discord
from discord import app_commands
from discord.ext import commands


from utils.views.button_menu import InteractionMenu
from utils.database.calls.users import Users

class MenuAdvanced_cog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.users_db=Users(bot.redis)

    @app_commands.command(name="app_command_menu_template_adv", description="<description>")
    async def advanced_menu(self, interaction: discord.Interaction):
        ## callback has to be defined before instantiating the class
        discord.ui.Button.callback = callback
        ## optional: add more utility to button callbacks
        discord.ui.Button.users_db = self.users_db
        ## Max rows = 5 (0-4)
        ## needs label
        ## row optional
        ## style optional
        ## url optional, will make the button not use the callback
        menu_options = [
            discord.ui.Button(label='Pie',emoji='🥧',row=0, style=discord.ButtonStyle.blurple,url='https://cnn.com'),
            discord.ui.Button(label='Cookies',emoji='🍪',row=1, style=discord.ButtonStyle.green),
            discord.ui.Button(label='Ice Cream',emoji='🍦',row=2, style=discord.ButtonStyle.red),
            discord.ui.Button(label='Cake',emoji='🎂',row=3, style=discord.ButtonStyle.grey)
        ]

        embed = discord.Embed(title="This is a dessert menu!")

        ## instantiate menu class
        menu = InteractionMenu(self.bot)
        ## see below for async callback
        ## Generate the menu view with the buttons
        menu_view = await menu.generate_view_advanced(menu_options, self.bot, interaction=interaction)

        ## Send the menu message
        await interaction.response.send_message(view=menu_view, embed=embed, ephemeral=True)


        ## if you are not sending an interaction, but rather a regular message and you want
        ## to be able to edit the original message inside the callback, you will need to add
        ## the message to each button with this method.
        #menu.allow_original_menu_updates(menu_view, menu_message)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MenuAdvanced_cog(bot))


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