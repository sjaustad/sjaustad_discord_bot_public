import discord, datetime, traceback
from discord import app_commands
from discord.ext import commands


from utils.views.button_menu import InteractionMenu
from utils.database.calls.users import Users
from utils.views.confirm import Confirm
from utils.messages.user_input import UserInput

from settings.server_settings import settings

## Date to end secret santa registration
close_date = datetime.datetime(2022, 12, 15, 23, 59)


class SecretSanta_cog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.users_db=Users(bot.redis)

    @app_commands.command(name="secretsanta", description="Display the secret santa menu")
    async def secret_santa(self, interaction: discord.Interaction):
        ## callback has to be defined before instantiating the class
        discord.ui.Button.callback = callback
        discord.ui.Button.users_db = self.users_db
        ## Max rows = 5 (0-4)
        ## needs label
        ## row optional
        ## style optional
        ## url optional, will make the button not use the callback
        menu_options = [
            discord.ui.Button(label='Join',emoji='🎄',row=0, style=discord.ButtonStyle.green),
            discord.ui.Button(label='Withdraw',emoji='🚫',row=0, style=discord.ButtonStyle.red),
            discord.ui.Button(label='Update Address',emoji='🏠',row=1, style=discord.ButtonStyle.grey),
            discord.ui.Button(label='Update Interests',emoji='🎾',row=1, style=discord.ButtonStyle.grey),
            discord.ui.Button(label='View my information',emoji='🔍',row=2, style=discord.ButtonStyle.grey),
        ]

        ## Post registration options
        current_time = datetime.datetime.now()
        if current_time > close_date: 
            menu_options.append(discord.ui.Button(label='Add/Update Tracking or Confirm Sent',emoji='📦',row=3, style=discord.ButtonStyle.grey))
            menu_options.append(discord.ui.Button(label='Mark gift received',emoji='🎁',row=3, style=discord.ButtonStyle.grey))
            menu_options.append(discord.ui.Button(label='Send message to my recipient',emoji='📩',row=4, style=discord.ButtonStyle.grey))
            menu_options.append(discord.ui.Button(label='Send message to my secret santa',emoji='🎅',row=4, style=discord.ButtonStyle.grey))

        secret_santa_data = await self.users_db.get_attribute(interaction.user.id, "secret_santa")

       
        
        embed = discord.Embed(title="Secret Santa menu")

        if secret_santa_data is not None:
            if secret_santa_data['santa_for'] is not None:
                recipient_info = await self.users_db.get_attribute(secret_santa_data['santa_for'], "secret_santa")
                embed.add_field(name="Buy a gift for:", value=self.bot.get_user(secret_santa_data['santa_for']).name, inline=False)
                ## check if tracking added
                if secret_santa_data['sent'] is False:
                    embed.add_field(name="⚠️ Alert", value="Gift to your recipient not marked as sent",inline=False)
                elif recipient_info['received'] is True:
                    embed.add_field(name="🎁 Note", value=f"Your recipient has marked their gift received. Thank you!",inline=False)
                else:
                    embed.add_field(name="⚠️ Alert", value=f"Your recipient has not received their gift yet.",inline=False)

                if secret_santa_data['received'] is True:
                    embed.add_field(name="🎁 Note", value=f"You have marked your gift as received!",inline=False)
                elif secret_santa_data['tracking'] is not None:
                    embed.add_field(name="🔔 Update", value=f"Your gift has been sent to you. \nTracking Info/Notes: {secret_santa_data['tracking']}",inline=False)

                


                ## display recipient info
                ## format address
                recipient_address = f"""Contact:
                {recipient_info['address']} {recipient_info['city']}, {recipient_info['state']} {recipient_info['zip']}
                {recipient_info['email']}
                """

                recipient_interests = f"""
                Interests: {recipient_info['interests']}
                Steam User: {recipient_info['steam_user']}
                Favorite Movie: {recipient_info['favorite_movie']}
                Favorite TV: {recipient_info['favorite_tv']}
                Favorite Food: {recipient_info['favorite_food']}
                """

                embed.add_field(name="User Interests",value=recipient_interests,inline=False)
                embed.add_field(name="Address/Contact",value=recipient_address, inline=False)
                
                #recipient = self.users_db.get_attribute(secret_santa_data['santa_for'], "secret_santa")
                #if recipient['sent']
            if secret_santa_data['address'] is None or secret_santa_data['address'] == '' or secret_santa_data['email'] is None or secret_santa_data['email'] == '':
                embed.add_field(name="⚠️ Warning ⚠️",value="Missing one or more address fields!",inline=False)
        embed.add_field(name="Registration closes", value=f"{close_date.strftime('%a, %m-%d-%Y %I:%M %p')}")
        embed.add_field(name="Price Range", value=f"$15-25")
        all_ss_users = await self.users_db.get_one_attribute_all_users("secret_santa")
        embed.add_field(name='Total registered:',value=len(all_ss_users))

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
    await bot.add_cog(SecretSanta_cog(bot))


async def callback(self, interaction: discord.Interaction) -> None:

    ## if they choose cancel
    if self.value.lower() == "cancel":
        return await self.menu_message.edit_original_response(content=f"Cancelled menu.", view=None, embed=None)
    if self.index == 0: # join
        await join_secret_santa(self, interaction)
    if self.index == 1: # withdraw
        await withdraw_secret_santa(self, interaction)
    if self.index == 2: # address
        await update_address(self, interaction)
    if self.index == 3: # interests
        await update_interests(self, interaction)
    if self.index == 4: # add tracking
        await view_information(self, interaction)
    if self.index == 5: # add tracking
        await add_tracking(self, interaction)
    if self.index == 6: # add tracking
        await mark_received(self, interaction)
    if self.index == 7: # add tracking
        await message_recipient(self, interaction)
    if self.index == 8: # add tracking
        await message_santa(self, interaction)

    ## create new embed
    #new_embed = discord.Embed(title=f"You selected {self.value} at menu index {self.index}")
    ## remove the options and send new embed to original message
    #await self.menu_message.edit_original_response(view=None)

    ## if the original message sent is not ephemeral (user only) you can delete it, otherwise you cannot
    #await self.menu_message.delete_original_response()
async def message_recipient(context, interaction: discord.Interaction):
    ## check if they have attributes
    secret_santa_dict = await context.users_db.get_attribute(interaction.user.id, "secret_santa")
    ## check if assignment has happened
    if secret_santa_dict['santa_for'] is None: return await interaction.response.send_message(f"{interaction.user.mention}, you haven't received a santa assignment yet!",ephemeral=True)
    ## send modal
    await interaction.response.send_modal(message_modal(context.bot, context.users_db, secret_santa_dict, embed_title="New message from your secret santa", return_message = f"To respond to your secret santa, use the command `/secretsanta` and select the option \"Send message to my secret santa.\"", return_title="Instructions"))



async def message_santa(context, interaction: discord.Interaction):
    ## check if they have attributes 
    secret_santa_dict = await context.users_db.get_attribute(interaction.user.id, "secret_santa")
    if secret_santa_dict['their_santa'] is None: return await interaction.response.send_message(f"{interaction.user.mention}, you haven't received a santa yet!",ephemeral=True)
    ## send modal
    await interaction.response.send_modal(message_modal(context.bot, context.users_db, secret_santa_dict, embed_title="New message from your secret santa recipient", return_message = f"To respond to your recipient, use the command `/secretsanta` and select the option \"Send message to my recipient.\"", return_title="Instructions"))

async def view_information(context, interaction: discord.Interaction):
    ## See if they are in the secret santa or not
    secret_santa_data = await context.users_db.get_attribute(interaction.user.id, "secret_santa")

    if secret_santa_data is None:
        return await interaction.response.send_message(f"You have not signed up for Secret Santa! Use the menu to join.", ephemeral=True)
    
    ## embeds have literally no error handling so I have do baby it
    info_embed = discord.Embed(title="Secret Santa Information")
    interests = "\u200b" if secret_santa_data['interests'] is None or secret_santa_data['interests'] == '' else secret_santa_data['interests']
    steam_user = "\u200b" if secret_santa_data['steam_user'] is None or secret_santa_data['steam_user'] == '' else secret_santa_data['steam_user']
    movie = "\u200b" if secret_santa_data['favorite_movie'] is None or secret_santa_data['favorite_movie'] == '' else  secret_santa_data['favorite_movie']
    tv = "\u200b" if secret_santa_data['favorite_tv'] is None or secret_santa_data['favorite_tv'] == '' else secret_santa_data['favorite_tv']
    food = "\u200b" if secret_santa_data['favorite_food'] is None or secret_santa_data['favorite_food'] == '' else secret_santa_data['favorite_food']
    
    
    
    info_embed.add_field(name="Personal Info", value="\u200b")
    info_embed.add_field(name="Interests",value=interests,inline=False)
    info_embed.add_field(name="Steam Username",value=steam_user)
    info_embed.add_field(name="Movie:",value=movie)
    info_embed.add_field(name="TV Show:",value=tv)
    info_embed.add_field(name="Food:",value=food)
    info_embed.add_field(name="**Contact Information**",value="\u200b", inline=False)

    ## embeds have literally no error handling so I have do baby it
    address = "\u200b" if secret_santa_data['address'] is None or secret_santa_data['address'] == '' else secret_santa_data['address']
    city = "\u200b" if secret_santa_data['city'] is None or secret_santa_data['city'] == '' else secret_santa_data['city']
    zip = "\u200b" if secret_santa_data['zip'] is None or secret_santa_data['zip'] == '' else secret_santa_data['zip']
    state = "\u200b" if secret_santa_data['state'] is None or secret_santa_data['state'] == '' else secret_santa_data['state']
    email = "\u200b" if secret_santa_data['email'] is None or secret_santa_data['email'] == '' else secret_santa_data['email']
        

    info_embed.add_field(name="Address",value=address)
    info_embed.add_field(name="City",value=city)
    info_embed.add_field(name="Zip",value=zip)
    info_embed.add_field(name="State",value=state)
    info_embed.add_field(name="Email",value=email)

    await interaction.response.send_message(embed=info_embed, ephemeral=True)



async def join_secret_santa(context, interaction: discord.Interaction):

    ## See if they are in the secret santa or not
    secret_santa_dict = await context.users_db.get_attribute(interaction.user.id, "secret_santa")

    if secret_santa_dict is not None:
        return await interaction.response.send_message(f"You have already signed up for Secret Santa! Use the menu to withdraw or update your information if needed.", ephemeral=True)

    
    ## user data agreement
    eula_warning = "Data collected for the purpose of secret santa will not be divulged to anyone except the person assigned to be your secret santa or a moderator if needed. This data is not publicly available. It is stored in a password protected database. Measures are taken to ensure restricted access to machines running this discord bot. Data provided for secret santa is deleted shortly after the conclusion of tha activity, before Jan 1 of next year. Continuing confirms your agreement to share data expressly for the purpose of the secret santa activity and acknowledging that it will not be used in any other way."
    # user_response = await Confirm.display(interaction=interaction,text=eula_warning,cancel_text="No changes made.")
    # if user_response is None or user_response is False: return

    options = ['Continue'] 
    embed = discord.Embed(title="User data sharing agreement")
    

    ## instantiate menu class
    menu = InteractionMenu(context.bot)
    ## define the call back for the custom_button
    ## see below for async callback
    menu.custom_button.callback = eula_callback
    menu.custom_button.users_db = context.users_db
    menu.custom_button.context = context
    menu.custom_button.secret_santa_dict = secret_santa_dict
    ## Generate the menu view with the buttons
    menu_view = await menu.generate_view(options, interaction=interaction)
    ## Send the menu message
    await interaction.response.send_message(content=eula_warning, view=menu_view, ephemeral=True)


async def eula_callback(self, interaction: discord.Interaction) -> None:
    if self.value.lower() == "cancel":
        return await self.menu_message.edit_original_response(content=f"Cancelled menu.", view=None, embed=None)
    
    ## remove the options and send new embed to original message
    await self.menu_message.edit_original_response(view=None)


    current_time = datetime.datetime.now()
    ## validate current time that registration isn't closed
    if current_time > close_date: 
        return await interaction.response.send_message(f"Registration for this year's secret santa has closed.", ephemeral=True)
    await interaction.response.send_modal(personal_information_modal(self.context.bot,self.context.users_db,santa_dict=self.secret_santa_dict,chain=True))


    
    

async def withdraw_secret_santa(context, interaction: discord.Interaction):
    secret_santa_data = await context.users_db.get_attribute(interaction.user.id, "secret_santa")
    if secret_santa_data is None:
        return await interaction.response.send_message(f"You are not currently signed up for secret santa", ephemeral=True)
    current_time = datetime.datetime.now()
    if current_time > close_date: 
        return await interaction.response.send_message(f"You cannot withdraw after registration has closed!",ephemeral=True)
    await context.users_db.remove_attribute(interaction.user.id, "secret_santa")
    return await interaction.response.send_message(f"{interaction.user.mention}, you have left the secret santa festivities...",ephemeral=True)


async def update_address(context, interaction:discord.Interaction):
    await interaction.response.send_modal(address_modal(context.bot,context.users_db))

async def update_interests(context, interaction:discord.Interaction):
    santa_dict = await context.users_db.get_attribute(interaction.user.id, "secret_santa")
    await interaction.response.send_modal(personal_information_modal(context.bot,context.users_db,santa_dict))

async def add_tracking(context, interaction:discord.Interaction):
    current_time = datetime.datetime.now()
    if current_time < close_date: 
        return await interaction.response.send_message("Tracking feature not active until after registration date closes!", ephemeral=True)
    else:
        await interaction.response.send_modal(tracking_modal(context.bot, context.users_db))



## Modals

class personal_information_modal(discord.ui.Modal, title="Secret Santa personal information"):
    def __init__(self, bot, users_db, chain=False, santa_dict=None):
        super().__init__()
        self.bot = bot
        self.users_db = users_db
        self.chain = chain
        self.santa_dict = santa_dict
        ### alternativevly:
        # self.interests = discord.ui.TextInput(...)
        # self.steam_user = discord.ui.TextInput(...)

    interests = discord.ui.TextInput(
        label='Briefly describe interests you have',
        placeholder="Singing, baking, legos, etc",
        style=discord.TextStyle.long,
        required=True,
        #default = None if santa_dict['interests'] is None or santa_dict['interests'] == '' else santa_dict['interests']
    )    
    steam_user = discord.ui.TextInput(
        label='What is your Steam username?',
        placeholder="Check if your wishlist is public",
        required=False,
        max_length=600
    )
    fav_movie = discord.ui.TextInput(
        label='What is your favorite movie?',
        required=False,
        max_length=600
    )
    fav_tv = discord.ui.TextInput(
        label='What is your favorite TV show?',
        required=False,
        max_length=600,
    )
    fav_food = discord.ui.TextInput(
        label='What is your favorite food?',
        required=False,
        max_length=600,
    )


    async def on_submit(self, interaction: discord.Interaction):

        await interaction.response.send_message(f'Personal information setfor secret santa. Add your contact info to complete registration.', ephemeral=True)
        santa_dict = await self.users_db.get_attribute(interaction.user.id, "secret_santa")
        if santa_dict is None:
            ## upload information to DB
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
                'address':None,
                'zip':None,
                'city':None,
                'state':None,
                'email':None,
                ## User info to help Santa
                'interests':self.interests.value,
                'steam_user':self.steam_user.value,
                'favorite_movie':self.fav_movie.value,
                'favorite_tv':self.fav_tv.value,
                "favorite_food":self.fav_food.value
            }
        else:
            santa_dict['interests'] = self.interests.value
            santa_dict['steam_user'] = self.steam_user.value
            santa_dict['favorite_movie'] = self.fav_movie.value
            santa_dict['favorite_tv'] = self.fav_tv.value
            santa_dict['favorite_food'] = self.fav_food.value

        await self.users_db.set_attribute(interaction.user.id, "secret_santa", santa_dict)


        ## send feedback
        test_channel = self.bot.get_channel(getattr(settings.guilds,str(interaction.guild.id)).server.channels.testchannel)
        
        santa_embed = discord.Embed(title="secret santa personal information updated", description=f"{test_channel.mention}")
        santa_embed.add_field(name="From",value=f"{interaction.user.mention}")

        await test_channel.send(embed=santa_embed)


        if self.chain is True:
            ## I HATE DISCORD
            ## this stupid button is only because discord won't allow chaining modals because they apparently
            ## can't conceive of a time when people would want to chain two modals together. I create this button
            ## so the user can start a new interaction by clicking the damn button


            options = ['Add Contact Info'] ## lol, you get one option

            embed = discord.Embed(title="Click below to add your contact info")

            ## instantiate menu class
            menu = InteractionMenu(self.bot)
            ## define the call back for the custom_button
            ## see below for async callback
            menu.custom_button.callback = address_callback
            menu.custom_button.users_db = self.users_db
            ## Generate the menu view with the buttons
            menu_view = await menu.generate_view(options, interaction=interaction)
            ## Send the menu message
            await interaction.followup.send(view=menu_view, embed=embed, ephemeral=True)

        

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        try:
            await interaction.response.send_message('Oops this is embarassing! Something went wrong. Contact bot owner.', ephemeral=True)
        except discord.errors.InteractionResponded:
            await interaction.followup.send(content='Oops this is embarassing! Something went wrong. Contact bot owner.', ephemeral=True)

        # Make sure we know what the error actually is
        traceback.print_tb(error.__traceback__)

class address_modal(discord.ui.Modal, title="Secret Santa address"):
    def __init__(self, bot, users_db):
        super().__init__()
        self.bot = bot
        self.users_db = users_db

    street_address = discord.ui.TextInput(
        label='Street Address:',
        placeholder="Do not forget apartment numbers",
        required=False,

    )    
    zip = discord.ui.TextInput(
        label='Zip:',
        required=False
    )
    city = discord.ui.TextInput(
        label='City:',
        required=False
    )
    state = discord.ui.TextInput(
        label='State:',
        required=False
    )
    email = discord.ui.TextInput(
        label='Email Address:',
        required=False
    )
    async def on_submit(self, interaction: discord.Interaction):
        ## get current dict
        santa_dict = await self.users_db.get_attribute(interaction.user.id, "secret_santa")


        santa_dict['address']=self.street_address.value
        santa_dict['zip']=self.zip.value
        santa_dict['city']=self.city.value
        santa_dict['state']=self.state.value
        santa_dict['email']=self.email.value

        await self.users_db.set_attribute(interaction.user.id, "secret_santa", santa_dict)


        ## send feedback
        test_channel = self.bot.get_channel(getattr(settings.guilds,str(interaction.guild.id)).server.channels.testchannel)
        
        santa_embed = discord.Embed(title="Secret santa address updated!", description=f"{test_channel.mention}")
        santa_embed.add_field(name="From",value=f"{interaction.user.mention}")

        await test_channel.send(embed=santa_embed)
        await interaction.response.send_message(f'Contact information added!', ephemeral=True)


    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        try:
            await interaction.response.send_message('Oops this is embarassing! Something went wrong with the address modal. Contact bot owner.', ephemeral=True)
        except discord.errors.InteractionResponded:
            await interaction.followup.send(content='Oops this is embarassing! Something went wrong with the address modal. Contact bot owner.', ephemeral=True)


        # Make sure we know what the error actually is
        traceback.print_tb(error.__traceback__)



class tracking_modal(discord.ui.Modal, title="Add Tracking/Notes"):
    def __init__(self, bot, users_db):
        super().__init__()
        self.bot = bot
        self.users_db = users_db

    tracking = discord.ui.TextInput(
        label='Tracking Number/Delivery Date/Notes',
        placeholder="Make a note if electronic delivery",
        required=False,

    )    

    async def on_submit(self, interaction: discord.Interaction):
        ## get current user santa dict
        santa_dict = await self.users_db.get_attribute(interaction.user.id, "secret_santa")
        ## set sent to true
        santa_dict['sent'] = True
    
        ## update recipient with tracking number
        recipient_dict = await self.users_db.get_attribute(santa_dict['santa_for'], "secret_santa")
        recipient_dict['tracking'] = self.tracking.value
        if recipient_dict['tracking'] == '': 
            recipient_dict['tracking'] = None
            santa_dict['sent'] = False

        ## update database
        await self.users_db.set_attribute(interaction.user.id, "secret_santa", santa_dict)
        await self.users_db.set_attribute(santa_dict['santa_for'], "secret_santa", recipient_dict)

        ## send feedback
        await interaction.response.send_message(f'Tracking information added! Your recipient has been notified.', ephemeral=True)

        ## send recipient a notification
        discord_recipient = self.bot.get_user(santa_dict['santa_for'])
        discord_dm = await discord_recipient.create_dm()
        
        tracking_embed = discord.Embed(title=f"Secret santa update", description="Your secret santa has marked your gift as sent")
        tracking_embed.add_field(name="Tracking information:", value=self.tracking.value) 
        await discord_dm.send(embed=tracking_embed)


    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        try:
            await interaction.response.send_message('Oops this is embarassing! Something went wrong with the tracking modal. Contact bot owner.', ephemeral=True)
        except discord.errors.InteractionResponded:
            await interaction.followup.send(content='Oops this is embarassing! Something went wrong with the tracking modal. Contact bot owner.', ephemeral=True)


        # Make sure we know what the error actually is
        traceback.print_tb(error.__traceback__)


class message_modal(discord.ui.Modal, title="Secret santa: send message"):
    def __init__(self, bot, users_db, secret_santa_dict,embed_title="Send Message", return_title=None, return_message = None):
        super().__init__()
        self.bot = bot
        self.users_db = users_db
        self.secret_santa_dict = secret_santa_dict
        self.return_title = return_title
        self.return_message = return_message
        self.embed_title=embed_title

    message = discord.ui.TextInput(
        label='Message to send',
        style=discord.TextStyle.long,
        required=True

    )    

    async def on_submit(self, interaction: discord.Interaction):

        ## create DM
        recipient = self.bot.get_user(self.secret_santa_dict['santa_for'])
        dm_message = await recipient.create_dm()

        ## create embed
        message_embed = discord.Embed(title=self.embed_title)
        message_embed.add_field(name="Message", value=self.message.value,inline=False)
    
        if self.return_title is not None and self.return_message is not None:
            message_embed.add_field(name=self.return_title, value=self.return_message)

        ## send message
        await dm_message.send(embed=message_embed)

        await interaction.response.send_message(f"Message sent successfully!", ephemeral=True)


    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        try:
            await interaction.response.send_message('Oops this is embarassing! Something went wrong with the message modal. Contact bot owner.', ephemeral=True)
        except discord.errors.InteractionResponded:
            await interaction.followup.send(content='Oops this is embarassing! Something went wrong with the message modal. Contact bot owner.', ephemeral=True)


        # Make sure we know what the error actually is
        traceback.print_tb(error.__traceback__)


async def address_callback(self, interaction: discord.Interaction) -> None:
    await interaction.response.send_modal(address_modal(self.bot,self.users_db))
    #await interaction.response.send_modal(feedback_modal(self.bot))
    ## if they choose cancel
    if self.value.lower() == "cancel":
        return await self.menu_message.edit_original_response(content=f"Cancelled menu.", view=None, embed=None)
    
    ## remove the options and send new embed to original message
    await self.menu_message.edit_original_response(view=None)

    ## if the original message sent is not ephemeral (user only) you can delete it, otherwise you cannot
    #await self.menu_message.delete_original_response()

async def mark_received(context, interaction:discord.Interaction):
    secret_santa_dict = await context.users_db.get_attribute(interaction.user.id, "secret_santa")
    if secret_santa_dict['their_santa'] is None: return await interaction.response.send_message(f"{interaction.user.mention}, you haven't received a santa assignment yet!",ephemeral=True)

    options = ['Yes'] 
    embed = discord.Embed(title="Collection Confirmation")


    
    ## instantiate menu class
    menu = InteractionMenu(context.bot)
    ## define the call back for the custom_button
    ## see below for async callback
    menu.custom_button.callback = collection_confirmation_callback

    menu.custom_button.users_db = context.users_db
    menu.custom_button.context = context
    menu.custom_button.secret_santa_dict = secret_santa_dict

    ## check if button will be for marking as received or unmarking
    if secret_santa_dict['received'] is False:
        received_text = "Have you received your gift from your secret santa either electronically or through mail?"
        menu.custom_button.remove = False
    else:
        received_text = "Are you sure you want to unmark your gift as received?"
        menu.custom_button.remove = True


    ## Generate the menu view with the buttons
    menu_view = await menu.generate_view(options, interaction=interaction)
    ## Send the menu message
    await interaction.response.send_message(content=received_text, view=menu_view, ephemeral=True)


async def collection_confirmation_callback(self, interaction: discord.Interaction) -> None:
    if self.value.lower() == "cancel":
        return await self.menu_message.edit_original_response(content=f"Cancelled collection confirmation", view=None, embed=None)
    
    ## remove the options and send new embed to original message
    await self.menu_message.edit_original_response(view=None)

    if self.remove is False:
        await interaction.response.send_message(f"{interaction.user.mention}, you have marked your gift as received. Thank you!", ephemeral=True)
        self.secret_santa_dict['received'] = True
        await self.users_db.set_attribute(interaction.user.id, "secret_santa", self.secret_santa_dict)
    
    else:
        await interaction.response.send_message(f"{interaction.user.mention}, you have marked your gift as not received.", ephemeral=True)
        self.secret_santa_dict['received'] = False
        await self.users_db.set_attribute(interaction.user.id, "secret_santa", self.secret_santa_dict)


