from code import interact
import discord, traceback
from discord import app_commands
from discord.ext import commands
import asyncio, random
from dateutil.parser import parse


from utils.views.button_menu import InteractionMenu

from plugins.gamepass_finder.GamepassDBFunctions import GamepassDBFunctions

from utils.messages.user_input import UserInput


class Game_cog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.gamepass_db = GamepassDBFunctions(bot.redis)

    @app_commands.command(name="game", description="Select random game from Xbox Gamepass or get more info on a specific game")
    async def game(self, interaction: discord.Interaction):
        

        embed = discord.Embed(title="Game Assistant")

        ## instantiate menu class
        game_main_menu = InteractionMenu(self.bot)
        menu_options = ["Random Game"]#, "Game Info"]
        ## define the call back for the custom_button

        ## see below for async callback
        ## pass anyother variables needed for callback
        game_main_menu.custom_button.callback = main_menu_callback
        game_main_menu.custom_button.gamepass_db = self.gamepass_db

        ## Generate the menu view with the buttons
        menu_view = await game_main_menu.generate_view(menu_options, interaction=interaction)
        ## Send the menu message
        await interaction.response.send_message(view=menu_view, embed=embed, ephemeral=True)


        ## if you are not sending an interaction, but rather a regular message and you want
        ## to be able to edit the original message inside the callback, you will need to add
        ## the message to each button with this method.
        #menu.allow_original_menu_updates(menu_view, menu_message)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Game_cog(bot))




## Define helper functions anywhere outside of the class
async def random_game(interaction, bot, gamepass_db, menu_message):
    random_game_menu_embed = discord.Embed(title="Do you want a multiplayer or single player game?")
    random_game_menu_options = ['single player','multiplayer','either']
    random_game_menu = InteractionMenu(bot)
    random_game_menu.custom_button.callback = random_menu_callback
    random_game_menu.custom_button.gamepass_db = gamepass_db

    random_game_view = await random_game_menu.generate_view(random_game_menu_options, interaction=menu_message)

    await menu_message.edit_original_response(view=random_game_view, embed=random_game_menu_embed)



## callbacks
async def main_menu_callback(self, interaction: discord.Interaction) -> None:
    await self.menu_message.edit_original_response(view=None)
    await interaction.response.defer(ephemeral=True)
    ## if they choose cancel
    if self.value.lower() == "cancel":
        return 

    if self.index == 0:
        ## random game
        await random_game(interaction, self.bot, self.gamepass_db, self.menu_message)

    if self.index == 1:
        ## get game info
        await game_search(interaction, self.bot, self.gamepass_db)


async def random_menu_callback(self, interaction: discord.Interaction) -> None:
    await interaction.response.defer(ephemeral=True)
    await self.menu_message.edit_original_response(view=None)
    ## if they choose cancel
    if self.value.lower() == "cancel":
        return await self.menu_message.edit_original_response(view=None)

    all_games = await self.gamepass_db.retrieve_all_games()

    if self.index == 0:
        game_filter = "single-player"
    elif self.index == 1:
        game_filter = "multi"
    elif self.index == 2:
        game_filter = "any"



    valid_list = []
    for game in all_games:
        if 'game_modes' in game['value']:
            if len(game['value']['game_modes']) < 2 and len(game['value']['game_modes']) > 0 and game_filter == "single-player":
                valid_list.append(game)
            elif len(game['value']['game_modes']) > 1 and game_filter == "multi":
                valid_list.append(game)
            if game_filter == "any":
                valid_list.append(game)
        else: continue

    image_path = self.bot.settings.server.base_dir  + "/plugins/gamepass_finder/"
    file = discord.File(image_path + "image_scroll.gif")
    
    random_embed = discord.Embed(title="Choosing random game")
    random_embed.set_image(url=f"attachment://image_scroll.gif")
    #message = await interaction.edit_original_response(embed=random_embed, file=file)
    message = await interaction.channel.send(embed=random_embed, file=file)
    await asyncio.sleep(3)
    await message.delete()

    game_info = random.choice(valid_list)
    return await game_info_embed(interaction, game_info,description=f"Here is your randomly chosen game, selected from {len(valid_list)} games.")


async def game_info_embed(interaction, game_info, description = None):
    if 'value' in game_info:
        game_info = game_info['value']
    if description is not None:
        game_info_embed = discord.Embed(title=game_info['Game'], description = description)
    else:
        game_info_embed = discord.Embed(title=game_info['Game'])
    game_info_embed.add_field(name="Genre:",value=game_info['Genre (Giantbomb)'],inline=False)
    game_info_embed.add_field(name="Added to Gamepass:",value=parse(game_info['Added']).strftime('%m/%y'))
    game_info_embed.add_field(name="Release date:",value=parse(game_info['Release']).strftime('%m/%y'))
    

    if game_info['Metacritic'] != 0: game_info_embed.add_field(name="Metacritic score:",value=game_info['Metacritic'])

    if game_info['game_modes'][0] == '':
        game_info_embed.add_field(name="Game modes:",value="N/A")
    else:
        game_info_embed.add_field(name="Game modes:",value=", ".join(game_info['game_modes']))
    game_info_embed.set_image(url=game_info['cover_url'])
    await interaction.channel.send(embed=game_info_embed)
    #await interaction.response.send_message(embed=game_info_embed)

async def game_search(interaction, bot, gamepass_db):

    #user_response = await getResponse(ctx, discord.Embed(title="What is the name of the game you want to lookup?"))
    input = UserInput(bot)
    response = await input.get_text_response(user=interaction.user,channel=interaction.channel,embed=discord.Embed(title="What is the name of the game you want to lookup?"), timeout=60, interaction=interaction)

    if response['user_message']:
        game_info = await gamepass_db.retrieve_game(response['user_text'])
        if game_info is None:
            game_info = (await gamepass_db.retrieve_like_game(response['user_text']))[0]
        if game_info is None:
            return await interaction.response.send_message(f"{interaction.user.mention} sorry, could not find any games called {response['user_text']}")
        
        if isinstance(game_info, list):
            if len(game_info) > 1:
                choose_game_embed = discord.Embed(title="Multiple results found. Which one are you looking for?")
                choose_game_options = []
                for game in game_info:
                    choose_game_options.append(game['name'])
                choose_game_response = await displayMenu(ctx, choose_game_embed, choose_game_options)
                choice = choose_game_response['response']
                if choice is False: return
                await choose_game_response['message'].delete()
                game_info = game_info[choice]
            else:
                game_info = game_info[0]

        return await game_info_embed(interaction, game_info)