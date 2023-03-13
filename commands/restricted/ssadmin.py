import discord, traceback, random, copy, datetime
from discord import app_commands
from discord.ext import commands

from utils.views.button_menu import InteractionMenu
from utils.database.calls.users import Users
from utils.messages.user_input import UserInput


from settings.server_settings import settings
settings = settings()

## Role Auth import
from utils.auth.check_role import CheckRole
auth = CheckRole()


class Menu_cog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.users_db=Users(bot.redis)

    @app_commands.command(name="ssadmin", description="Secret santa admin")
    async def menu(self, interaction: discord.Interaction):
        if not auth.check_role(settings, interaction.guild, interaction.user, ['superadmin', 'sudo']): return await auth.not_auth_message(interaction=interaction)

        options = ['view registered users','mock assign','assign santas','delete data','show user info','force santa','update user data']

        embed = discord.Embed(title="Secret santa admin menu")

        ## instantiate menu class
        menu = InteractionMenu(self.bot)
        ## define the call back for the custom_button
        ## see below for async callback
        menu.custom_button.callback = callback
        menu.custom_button.users_db = self.users_db
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

    await self.menu_message.edit_original_response(view=None)

    if self.index == 0:
        await view_registered(interaction, self.bot, self.users_db)
    if self.index == 1:
        await mock_assign(interaction, self.bot, self.users_db)
    if self.index == 2:
        await assign_santas(interaction, self.bot, self.users_db)
    if self.index == 3:
        await delete_data(interaction)
    if self.index == 4:
        await show_user(interaction, self.bot, self.users_db)
    if self.index == 5:
        await force_assign(interaction, self.bot, self.users_db)
    if self.index == 6:
        await update_user_data(interaction,self.bot,self.users_db)

    ## if the original message sent is not ephemeral (user only) you can delete it, otherwise you cannot
    #await self.menu_message.delete_original_response()

async def update_user_data(interaction, bot, users_db):
    input = UserInput(bot)
    response = await input.get_text_response(user=interaction.user,channel=interaction.channel,embed=discord.Embed(title="User ID to check"), timeout=60, interaction=interaction)
    if not response['user_message']: return
    await interaction.edit_original_response(view=None)

    try:
        user_id = int(response['user_text'])
    except:
        await interaction.followup.send(content="User ID invalid", ephemeral=True)
    try:
        user = bot.get_user(user_id)
    except:
        await interaction.followup.send(content=f"Could not find user with ID {user_id}", ephemeral=True)

    santa_dict = {
        ## Santa Info
        'date': datetime.datetime.now(),
        'santa_for':None,
        'their_santa':None,
        ## Package info
        'sent':False,
        'received':False,
        'tracking':None,
        ## Address info
        'address':"1170 Cedar Heights Dr",
        'zip':"84341",
        'city':"Logan",
        'state':"Utah",
        'email':"ed.pingel15@gmail.com",
        ## User info to help Santa
        'interests':"Legos, Gaming, Star Wars, Cars, Airplanes, Helicopters, Porgraming,",
        'steam_user':"ravenrunner999",
        'favorite_movie':"Star Wars -- probably",
        'favorite_tv':"Right now, House of the Dragon",
        "favorite_food":"Steak."
    }
    await users_db.set_attribute(user_id, "secret_santa", santa_dict)
    await interaction.followup.send(content=f"Updated data for {user.name}")

async def show_user(interaction: discord.Interaction, bot, users_db):
    input = UserInput(bot)
    response = await input.get_text_response(user=interaction.user,channel=interaction.channel,embed=discord.Embed(title="User ID to check"), timeout=60, interaction=interaction)
    if not response['user_message']: return
    await interaction.edit_original_response(view=None)

    try:
        user_id = int(response['user_text'])
    except:
        await interaction.followup.send(content="User ID invalid", ephemeral=True)
    try:
        user = bot.get_user(user_id)
    except:
        await interaction.followup.send(content=f"Could not find user with ID {user_id}", ephemeral=True)

    user_santa_dict = await users_db.get_attribute(user_id, "secret_santa")
    if user_santa_dict is None: await interaction.followup.send(content=f"Could not find santa registration for user {user.name}.",ephemeral=True)

    embed= discord.Embed(title=f"Secret santa information for {user}")

    recipient_address = f"""Contact:
    {user_santa_dict['address']} {user_santa_dict['city']}, {user_santa_dict['state']} {user_santa_dict['zip']}
    {user_santa_dict['email']}
    """

    recipient_interests = f"""
    Interests: {user_santa_dict['interests']}
    Steam User: {user_santa_dict['steam_user']}
    Favorite Movie: {user_santa_dict['favorite_movie']}
    Favorite TV: {user_santa_dict['favorite_tv']}
    Favorite Food: {user_santa_dict['favorite_food']}
    """

    embed.add_field(name="User Interests",value=recipient_interests,inline=False)
    embed.add_field(name="Address/Contact",value=recipient_address, inline=False)
    if user_santa_dict['santa_for'] is not None:
        #embed.add_field(name="Santa for:",value=bot.get_user(user_santa_dict['santa_for']))
        embed.add_field(name="Santa for:",value="Assigned")
    else:
        embed.add_field(name="Santa for:",value="Not assigned")
    
    if user_santa_dict['their_santa'] is not None:
        #embed.add_field(name="Their santa:",value=bot.get_user(user_santa_dict['their_santa']))
        embed.add_field(name="Their santa:",value="Assigned")
    else:
        embed.add_field(name="Their santa:",value=f"Not assigned")
    
    
    await interaction.followup.send(embed=embed, ephemeral=True)
    
async def force_assign(interaction: discord.Interaction, bot, users_db):
    input = UserInput(bot)
    response = await input.get_text_response(user=interaction.user,channel=interaction.channel,embed=discord.Embed(title="User ID of santa to reassign"), timeout=60, interaction=interaction)
    if not response['user_message']: return
    await interaction.edit_original_response(view=None)

    try:
        user_id = int(response['user_text'])
    except:
        await interaction.followup.send(content="User ID invalid", ephemeral=True)
    try:
        user = bot.get_user(user_id)
    except:
        await interaction.followup.send(content=f"Could not find user with ID {user_id}", ephemeral=True)

    response = await input.get_text_response(user=interaction.user,channel=interaction.channel,embed=discord.Embed(title=f"User ID to assign to {user.name}"), timeout=60, interaction=interaction)
    
    try:
        assigned_user_id = int(response['user_text'])
    except:
        await interaction.followup.send(content="User ID invalid", ephemeral=True)
    try:
        assigned_user = bot.get_user(assigned_user_id)
    except:
        await interaction.followup.send(content=f"Could not find user with ID {assigned_user_id}", ephemeral=True)
    
    user_santa_dict = await users_db.get_attribute(user_id, "secret_santa")
    assigned_user_santa_dict = await users_db.get_attribute(assigned_user_id, "secret_santa")

    user_santa_dict['santa_for'] = assigned_user_id
    assigned_user_santa_dict['their_santa'] = user_id

    await users_db.set_attribute(user_id, "secret_santa", user_santa_dict)
    await users_db.set_attribute(assigned_user_id, "secret_santa", assigned_user_santa_dict)
    
    
    await interaction.followup.send(content=f"Force assigned new user", ephemeral=True)
                    


async def mock_assign(interaction, bot, users_db):

    all_ss_users = await run_assign(users_db)
    if all_ss_users is False: return await interaction.response.send_message(f"There must be at least more than one participant to start", ephemeral=True)
    

    santa_test_string = ""
    for santa in all_ss_users:
        santa_discord_user = bot.get_user(int(santa['key'].split(".")[1]))
        recipient_discord_user = bot.get_user(santa['value']['santa_for'])
        their_santa = bot.get_user(santa['value']['their_santa'])
        santa_test_string += f"{santa_discord_user.name} is santa for {recipient_discord_user.name}"
        santa_test_string += "\n"
        santa_test_string += f"Their santa is {their_santa.name}"
        santa_test_string += "\n\n"

    mock_santa_embed=discord.Embed(title="Mock Santa Assignments")
    mock_santa_embed.add_field(name="Assignments:",value=santa_test_string)
    await interaction.response.send_message(embed=mock_santa_embed, ephemeral=True)

async def run_assign(users_db):
    all_ss_users = await users_db.get_one_attribute_all_users("secret_santa")
    if len(all_ss_users) <= 1: return False

    random.shuffle(all_ss_users)
    available_people = copy.deepcopy(all_ss_users)

    for santa in all_ss_users:
        santa_id = int(santa['key'].split(".")[1])
        while True:
            recipient = random.choice(available_people)
            recipient_id = int(recipient['key'].split(".")[1])
            if recipient_id == santa_id:
                continue
            elif (recipient_id == 390683840299139084 and santa_id == 748311401625550928) or (santa_id == 390683840299139084 and recipient_id == 748311401625550928):
                continue
            else:
                avail_index = available_people.index(recipient)
                available_people.pop(avail_index)
                break
        ## assign santa
        ## if it can be done in one line, why do it in more?
        all_ss_users[all_ss_users.index([user for user in all_ss_users if int(user['key'].split(".")[1]) == recipient_id][0])]['value']['their_santa'] = santa_id
        santa['value']['santa_for'] = recipient_id

    return all_ss_users


async def view_registered(interaction, bot, users_db):
    all_ss_users = await users_db.get_one_attribute_all_users("secret_santa")

    users_text = ""
    for user in all_ss_users:
        user_id = int(user['key'].split(".")[1])
        discord_user = bot.get_user(user_id)
        users_text += f"{discord_user.name}"

        if user['value']['address'] is None or user['value']['address'] == "" or user['value']['email'] is None or user['value']['email'] == "":
            users_text += " - Missing address information ⚠️"
        
        users_text += "\n"
    santa_embed = discord.Embed(title="Registered users")
    santa_embed.add_field(name="User count:", value=len(all_ss_users),inline=False)
    santa_embed.add_field(name="Users:",value=users_text)

    await interaction.response.send_message(embed=santa_embed, ephemeral=True)


async def assign_santas(interaction: discord.Interaction, bot, users_db):
    all_ss_users = await run_assign(users_db)
    if all_ss_users is False: return await interaction.response.send_message(f"There must be at least more than one participant to start", ephemeral=True)


    status_message = ""
    for user in all_ss_users:
        try:
            ## update database values
            santa_dict = user['value']
            user_id = int(user['key'].split(".")[1]) 
            await users_db.set_attribute(user_id, "secret_santa", santa_dict)
            status_message += f"{bot.get_user(user_id).name} assigned successfully"
        except:
            status_message += f"Failed to assign {bot.get_user(user_id).name}"
        status_message += "\n"

        ## send private message
        santa_user = bot.get_user(user_id)
        discord_dm = await santa_user.create_dm()
        
        assignment_embed = discord.Embed(title=f"Secret santa update", description="HEY! DON'T PAY ATTENTION TO THE PREVIOUS ONE, THIS IS THE REAL SANTA ASSIGNMENT. Your secret santa recipient has been assigned!")
        assignment_embed.add_field(name="Santa assignment:", value=f"You have been assigned to get a gift for {bot.get_user(santa_dict['santa_for']).name}. Use the secret santa menu `\secretsanta` to see their interests and address as well as message them anonymously.") 
        await discord_dm.send(embed=assignment_embed)
        ## end send private message


    status_embed = discord.Embed(title="Assignment Status")
    status_embed.add_field(name=f"STATUS",value=status_message)

    await interaction.response.send_message(embed=status_embed)



async def delete_data(interaction):
    pass