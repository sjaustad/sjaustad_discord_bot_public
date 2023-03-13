import discord, traceback, datetime,copy
from discord import app_commands
from discord.ext import commands
from dateutil.parser import parse

from utils.views.button_menu import InteractionMenu
from utils.views.confirm import Confirm
from utils.views.dropdown import DropdownMenu
from utils.messages.user_input import UserInput


from utils.database.calls.votes import Votes

## Settings needed to get server roles
from settings.server_settings import settings
settings = settings()

## Role Auth import
from utils.auth.check_role import CheckRole
auth = CheckRole()



# Menu flow:
# Vote command

# Vote Menu --> ['Cast vote','My current votes','Polls','Run for council','Withdraw candidacy']
#   Cast vote           --> Get candidates and display list for each position   --> aggregate votes and send 
#   My current Votes
#   Polls
#   Run for council     --> Display menu to select position     --> Display modal to ask for information
#   Withdraw            --> confirmation menu about withdraw    --> run withdraw

# Admin vote menu --> []
#   


election_event = {
    'vote_start_date':datetime.datetime(2023, 1, 29, 0, 0),
    'vote_end_date':datetime.datetime(2023, 1, 31, 21, 59),
    'registration_start_date':datetime.datetime(2023, 1,9,0,0),
    'registration_end_date':datetime.datetime(2023,1,28,0,0),
    'flyer_url':"https://cdn.discordapp.com/attachments/776214261588164628/1061163967092891648/Election_Info_Poster-02.png",
    'open_positions':
    [
        {
            'slug':'council_leader',
            'title':'Council Leader',
            'description':'Responsible for maintaining functionality of the Oasis and providing direction and leadership to the Oasis council',
            'candidates':[],
        },
        {
            'slug':'moderation_chair',
            'title':'Moderation Chair',
            'description':'Responsible for moderating Oasis channels and ensuring rule and guidelines are kept in good order.',
            'candidates':[],
        },
        {
            'slug':'content_chair',
            'title':'Content Chair',
            'description':'Responsible for keeping server channels up to date and implementing new features, working with server bot developers, and keeping Oasis functions working.',
            'candidates':[],
        },
        {
            'slug':'engagement_chair',
            'title':'Engagement Chair',
            'description':'Responsible for organizing server events and engaging with server members to foster a fun and positive environment.',
            'candidates':[],
        },
    ],
    'voting_users':[]
}

class vote_menu_cog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.vote_db = Votes(bot.redis)

    @app_commands.command(name="vote", description="Displays the vote menu to users")
    async def vote_menu(self, interaction: discord.Interaction):
        embed = discord.Embed(title="Vote menu")

        ## setup embed
        ## get event and return if none
        election_event = await self.vote_db.get_election_event(interaction.guild.id)
        if election_event is None: return await interaction.response.send_message(f"{interaction.user.mention}, there is no election in your guild at this time.")
        ## list close date
        embed.add_field(name="Voting starts",value=election_event['vote_start_date'].strftime('%m/%d/%y %I:%M%p'),inline=True)
        embed.add_field(name="Voting ends",value=election_event['vote_end_date'].strftime('%m/%d/%y %I:%M%p'),inline=True)
        embed.add_field(name="Candidate registration ends",value=election_event['registration_end_date'].strftime('%m/%d/%y %I:%M%p'),inline=True)
        
        add_description = True
        if 'flyer_url' in election_event:
            if election_event['flyer_url'] is not None:
                embed.set_image(url=election_event['flyer_url'])
                add_description = False
        
        if add_description is True:

            ## List open positions
            open_positions_text = ""
            for position in election_event['open_positions']:
                open_positions_text += f"**{position['title']}**:\n {position['description']}\n\n"
            
            embed.add_field(name="\u200b", value="\u200b")
            embed.add_field(name="Open positions", value=open_positions_text,inline=False)



        ## setup menu
        options = ['View Candidates','Cast vote','My current votes','Polls','Run for council','Update candidate info','Withdraw candidacy']#,'Election info']

        

        ## instantiate menu class
        
        vote_menu = InteractionMenu(self.bot)
        ## define the call back for the custom_button
        ## see below for async callback
        vote_menu.custom_button.callback = vote_menu_callback
        vote_menu.custom_button.vote_db = self.vote_db
        vote_menu.custom_button.election = election_event
        ## Generate the menu view with the buttons
        vote_menu_view = await vote_menu.generate_view(options, interaction=interaction)
        ## Send the menu message
        await interaction.response.send_message(view=vote_menu_view, embed=embed, ephemeral=True)

    @app_commands.command(name="admin_vote", description="Displays the vote menu to users")
    async def vote_admin_menu(self, interaction: discord.Interaction):
        authorized_roles = ['superadmin', 'sudo']
        if not auth.check_role(settings, interaction.guild, interaction.user, authorized_roles): return await auth.not_auth_message(interaction=interaction)

    
        options = ['Reset election','Detailed Results','Simple Results','Delete user votes','Remove candidate']

        embed = discord.Embed(title="Vote menu")

        ## instantiate menu class
        admin_vote_menu = InteractionMenu(self.bot)
        ## define the call back for the custom_button
        ## see below for async callback
        admin_vote_menu.custom_button.callback = admin_vote_menu_callback
        admin_vote_menu.custom_button.vote_db = self.vote_db

        ## Generate the menu view with the buttons
        admin_menu_view = await admin_vote_menu.generate_view(options, interaction=interaction)
        ## Send the menu message
        await interaction.response.send_message(view=admin_menu_view, embed=embed, ephemeral=True)        

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(vote_menu_cog(bot))



async def add_user_to_election(interaction:discord.Interaction, election:dict, bot, vote_db):
    candidate = await vote_db.find_candidate(interaction.guild.id, interaction.user.id)
    if candidate: return await interaction.response.send_message(f"You are already registered as a candidate!",ephemeral=True)
    
    if election['registration_start_date'] > datetime.datetime.now():
        return await interaction.response.send_message(f"The registration period for this election has not started yet.", ephemeral=True)

    if election['registration_end_date'] < datetime.datetime.now():
        return await interaction.response.send_message(f"The registration period for this election has ended.", ephemeral=True)


    options = []
    for position in election['open_positions']:
        options.append(position['title'])

    embed = discord.Embed(title="Which position would you like to run for?")

    ## instantiate menu class
    menu = InteractionMenu(bot)
    ## define the call back for the custom_button
    ## see below for async callback
    menu.custom_button.callback = position_selection_callback
    menu.custom_button.vote_db = vote_db
    menu.custom_button.election = election
    ## Generate the menu view with the buttons
    menu_view = await menu.generate_view(options, interaction=interaction)
    ## Send the menu message
    await interaction.response.send_message(view=menu_view, embed=embed, ephemeral=True)  

async def update_candidate_info(interaction:discord.Interaction, election:dict, bot, vote_db):
    candidate = await vote_db.find_candidate(interaction.guild.id, interaction.user.id)
    if not candidate: return await interaction.response.send_message(f"You are not currently registered as a candidate.",ephemeral=True)
    if election['registration_start_date'] > datetime.datetime.now():
        return await interaction.response.send_message(f"The registration period for this election has not started yet.", ephemeral=True)

    if election['registration_end_date'] < datetime.datetime.now():
        return await interaction.response.send_message(f"The registration period for this election has ended.", ephemeral=True)

    await interaction.response.send_modal(Add_User_Info_Modal(bot, vote_db))

async def show_polls(interaction:discord.Interaction, bot, vote_db, admin=False):
    ## count all users
    ordered_election = await vote_db.get_ordered_votes(interaction.guild.id)

    if admin is False:

        if ordered_election['vote_start_date'] > datetime.datetime.now():
            return await interaction.response.send_message(f"The voting period for this election has not started yet.", ephemeral=True)
        if ordered_election['vote_end_date'] < datetime.datetime.now():
            current_voting = False
        else:
            current_voting = True
        ## disable poll viewing until they have voted
        if interaction.user.id not in ordered_election['voting_users']: return await interaction.response.send_message(f"Viewing polls is not allowed until you have voted!",ephemeral=True)
    else: current_voting = True

    embed = discord.Embed(title="Election results")
    for position in ordered_election['open_positions']:
        position_text = f""
        if len(position['candidates']) == 0:
            position_text += f"No candidates yet"
        else:
            for candidate in position['candidates']:
                try:
                    candidate_user_name = bot.get_user(candidate['id']).name
                except:
                    candidate_user_name = "N/A"

                if current_voting is True and admin is False:
                    position_text += f"{candidate['real_name']} ({candidate_user_name})\n"
                else:
                    position_text += f"{candidate['real_name']} ({candidate_user_name}) - {len(candidate['votes'])}\n"
        embed.add_field(name=f"{position['title']}",value=position_text,inline=False)
    try:
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except:
        await interaction.followup.send(embed=embed,ephemeral=True)

async def view_my_votes(interaction:discord.Interaction, bot, vote_db):
    user_votes = await vote_db.get_user_votes(interaction.guild.id, interaction.user.id)
    if user_votes is None: return await interaction.response.send_message(f"You have not voted yet", ephemeral=True)
    embed = discord.Embed(title="Your votes")
    for vote in user_votes:
        embed.add_field(name=vote['position_title'], value=bot.get_user(vote['candidate_id']).name)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

async def withdraw_election(interaction:discord.Interaction, bot, vote_db, user_id=None):

    ## if the user_id var is given, this is an override for an admin to remove someone
    if user_id:
        candidate = await vote_db.find_candidate(interaction.guild.id, user_id)
        if not candidate: return await interaction.followup.send(content=f"This user is not currently registered as a candidate.",ephemeral=True)
        await vote_db.remove_candidate(interaction.guild.id, user_id)
    else:
        candidate = await vote_db.find_candidate(interaction.guild.id, interaction.user.id)
        if not candidate: return await interaction.response.send_message(f"You are not currently registered as a candidate.",ephemeral=True)
        warning_text = f"You are currently registered as a candidate for the position {candidate['position_title']}. Withdrawing will forfeit all votes accrued for this position. Do you wish to continue?"
        user_response = await Confirm.display(interaction=interaction,text=warning_text,cancel_text="No changes made.")
        if user_response is None: return
        elif user_response:
            await vote_db.remove_candidate(interaction.guild.id, interaction.user.id)
            await interaction.edit_original_response(content='Candidacy withdrawn. You may re-register to run as another position.')
        else: return

async def cast_vote(interaction: discord.Interaction, bot, vote_db, election:dict):

    election = await vote_db.get_election_event(interaction.guild_id)

    if election['vote_start_date'] > datetime.datetime.now():
        return await interaction.response.send_message(f"The voting period for this election has not started yet.", ephemeral=True)

    if election['vote_end_date'] < datetime.datetime.now():
        return await interaction.response.send_message(f"The voting period for this election has ended.", ephemeral=True)


    ## disallow voting if the user has already voted
    if interaction.user.id in election['voting_users']: return await interaction.response.send_message(f"{interaction.user.mention}, you have already cast your vote in this election!",ephemeral=True)

    ## Notice section
    warning_text = f"Upon continuing you will be presented with {len(election['open_positions'])} prompt(s), one for each position. You must respond to each of them to vote for every position. Carefully study the candidates and their platforms before proceeding. Once you cast your vote you will not be able to change it."
    user_response = await Confirm.display(interaction=interaction,text=warning_text,cancel_text="Your vote has not been cast.")
    if user_response is None: return await interaction.delete_original_response()
    elif user_response:
        pass
    else: return await interaction.delete_original_response()
    await interaction.delete_original_response()

    if interaction.user.id in election['voting_users']: await vote_db.delete_user_votes(interaction.guild.id, interaction.user.id)



    #await interaction.response.defer(ephemeral=True)

    for position in election['open_positions']:
        if len(position['candidates']) == 0: continue
        candidate_embed = discord.Embed(title=f"Select one candidate you would like to vote into the position **{position['title']}**")
        
        candidate_list_discord = []
        candidate_list = []
        for candidate in position['candidates']:
            try:
                user_name = bot.get_user(candidate['id']).name
            except:
                user_name = "N/A"
            candidate_string = f"{candidate['real_name']} | {user_name}"
            if len(candidate['qualifications'])>150:
                quals = candidate['qualifications'][:150] + "..."
            else:
                quals = candidate['qualifications']
            if len(candidate['platform']) >150:
                plat = candidate['platform'][:150] + "..."
            else:
                plat = candidate['platform']
            candidate_text = f"Qualifications: {quals}\nPlatform: {plat}"
            candidate_embed.add_field(name=candidate_string, value=candidate_text, inline=False)
            
            candidate_list_discord.append(discord.SelectOption(label=candidate_string))

            candidate_vote_values = {
                'string':candidate_string,
                'id':candidate['id'],
                'position_slug':position['slug'],
                'position_title':position['title'],
                'vote_db':vote_db
            }
            candidate_list.append(candidate_vote_values)

        #new_interaction = await interaction.edit_original_response(embed=candidate_embed)
        
        
        await DropdownMenu.display(interaction, candidate_list_discord, embed=candidate_embed,bot=bot ,min_values=1, max_values=1, storage=candidate_list)
        DropdownMenu.ui.callback = position_dropdown_callback
        DropdownMenu.ui.vote_db = vote_db

    #await show_polls(interaction, bot, vote_db, election)

async def show_candidates(interaction:discord.Interaction, bot, vote_db):

    election = await vote_db.get_election_event(interaction.guild_id)

    #embed = discord.Embed(title="Candidates:")

    await interaction.response.defer(ephemeral=True)
    
    for position in election['open_positions']:
        position_text = f"**Position: {position['title']}**\n"
        
        candidate_text = ""
        #vote_text += f"**{position['title']}**\n"
        for candidate in position['candidates']:
            candidate_text += f"**Candidate: {candidate['real_name']} ({bot.get_user(candidate['id']).name})**\n**Qualifications:** {candidate['qualifications']}\n**Platform:** {candidate['platform']}\n\n"

        if candidate_text == "": candidate_text = 'No candidates yet'
        position_text += candidate_text
        #(name=f"Position: {position['title']}", value=candidate_text,inline=False)
        try:
            await interaction.followup.send(content=position_text, ephemeral=True)
        except:
            await interaction.followup.send(content=f"Couldn't display candidate for position {position['title']}. This is likely due to a character length error, please notify an admin.")
#### MODALS ####
class Add_User_Info_Modal(discord.ui.Modal, title="Run for council"):
    def __init__(self, bot, vote_db, position_slug=None):
        super().__init__()
        self.bot = bot
        self.vote_db = vote_db
        self.position_slug = position_slug

    real_name = discord.ui.TextInput(
        label='What is your real name?',
        style=discord.TextStyle.short,
        required=True,
        max_length=24
    )   
    
    qualifications = discord.ui.TextInput(
        label='What qualifies you to run?',
        style=discord.TextStyle.long,
        required=True,
        max_length=512
    )    
    platform = discord.ui.TextInput(
        label='How will you improve The Oasis?',
        style=discord.TextStyle.long,
        required=True,
        max_length=512
    )
    

    async def on_submit(self, interaction: discord.Interaction):
        pass
        ## now you can do anything you would like with the variables passed to __init__ when creating the modal
        ## e.g. self.users_db.get_attribute(interaction.user.id, "some_attribute")
        ## access variables:

        candidate = await self.vote_db.find_candidate(interaction.guild.id, interaction.user.id)
        if candidate is not None:
            await self.vote_db.update_candidate(interaction.guild.id, interaction.user.id, self.real_name.value,self.qualifications.value, self.platform.value)
        else:
            await self.vote_db.add_candidate(interaction.guild.id, interaction.user.id, self.real_name.value, self.position_slug, self.qualifications.value, self.platform.value)

            ## testing:
            # await self.vote_db.add_candidate(interaction.guild.id, 12345, "Bob", "council_leader", "No quals", "No platform")
            # await self.vote_db.add_candidate(interaction.guild.id, 12346, "Jill", "moderation_chair", "No quals", "No platform")
            # await self.vote_db.add_candidate(interaction.guild.id, 12347, "Joe", "content_chair", "No quals", "No platform")
            # await self.vote_db.add_candidate(interaction.guild.id, 12348, "Jane","council_leader" , "No quals", "No platform")

        await interaction.response.send_message(f"{interaction.user.mention}, you have registered as a candidate!", ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        ## If you are too lazy to keep track of whether the interaction was definitively responded to:
        try:
            await interaction.response.send_message('Oops this is embarassing! Something went wrong. Contact bot owner.', ephemeral=True)
        except discord.errors.InteractionResponded:
            await interaction.followup.send(content='Oops this is embarassing! Something went wrong. Contact bot owner.', ephemeral=True)
        # Make sure we know what the error actually is
        traceback.print_tb(error.__traceback__)

#### CALLBACKS ####
async def admin_vote_menu_callback(self, interaction: discord.Interaction) -> None:

    ## if they choose cancel
    if self.value.lower() == "cancel":
        return await self.menu_message.edit_original_response(content=f"Cancelled menu.", view=None, embed=None)
    
    if self.index == 0:
        return await interaction.response.send_message(f"This has been disabled for election protection. Re-enable in code if needed.", ephemeral=True)
        # await self.vote_db.store_election_event(election_event, interaction.guild.id)
        # return await interaction.response.send_message(f"Election stored in DB successfully.", ephemeral=True)
    if self.index == 1:
        ## display all votes by all users
        election = await self.vote_db.get_election_event(interaction.guild.id)

        embed = discord.Embed(title="Detailed Election Results")
        
        for position in election['open_positions']:
            
            vote_text = ""
            #vote_text += f"**{position['title']}**\n"
            for candidate in position['candidates']:
                vote_text += f"Candidate: {self.bot.get_user(candidate['id']).name}\n\nVotes:{len(candidate['votes'])}\nVoters:\n"
                for vote in candidate['votes']:
                    vote_text += f"{self.bot.get_user(vote).name}\n"
                vote_text += "\n\n"
            if vote_text == "": vote_text = '\u200b'
            embed.add_field(name=f"Position: {position['title']}", value=vote_text,inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    if self.index == 2:
        await show_polls(interaction,self.bot, self.vote_db, admin=True)

    if self.index == 3:
        input = UserInput(self.bot)
        response = await input.get_text_response(user=interaction.user,channel=interaction.channel,embed=discord.Embed(title="User ID to check"), timeout=60, interaction=interaction)
        if not response['user_message']: return
        await interaction.delete_original_response()

        try:
            user_id = int(response['user_text'])
        except:
            await interaction.followup.send(content="User ID invalid", ephemeral=True)
        try:
            user = self.bot.get_user(user_id)
        except:
            await interaction.followup.send(content=f"Could not find user with ID {user_id}", ephemeral=True)

        try:
            await self.vote_db.delete_user_votes(interaction.guild.id, user.id)
            await interaction.followup.send(content=f"Deleted votes for {user.name}", ephemeral=True)
        except:
            await interaction.followup.send(content=f"Failed to delete votes for {user.name}", ephemeral=True)    


    if self.index == 4:
        input = UserInput(self.bot)
        response = await input.get_text_response(user=interaction.user,channel=interaction.channel,embed=discord.Embed(title="User ID to check"), timeout=60, interaction=interaction)
        if not response['user_message']: return
        await interaction.delete_original_response()

        try:
            user_id = int(response['user_text'])
        except:
            await interaction.followup.send(content="User ID invalid", ephemeral=True)
        try:
            user = self.bot.get_user(user_id)
        except:
            await interaction.followup.send(content=f"Could not find user with ID {user_id}", ephemeral=True)

        await withdraw_election(interaction, self.bot, self.vote_db, user_id=user_id)
        await interaction.followup.send(content=f"{user.name} removed from the election.",ephemeral=True)

    if self.index == 5:
        pass

async def vote_menu_callback(self, interaction: discord.Interaction) -> None:

    ## if they choose cancel
    if self.value.lower() == "cancel":
        return await self.menu_message.edit_original_response(content=f"Cancelled menu.", view=None, embed=None)
    ## view candidatse
    if self.index == 0:
        await show_candidates(interaction,self.bot, self.vote_db)
    ## Vote in election
    if self.index == 1:
        await cast_vote(interaction, self.bot, self.vote_db, self.election)
    ## view my current votes
    if self.index == 2:
        await view_my_votes(interaction,self.bot, self.vote_db)
    ## view polls
    if self.index == 3:
        await show_polls(interaction,self.bot, self.vote_db)
    ## run for councils
    if self.index == 4:
        await add_user_to_election(interaction, self.election, self.bot, self.vote_db)
    ## update candidate info
    if self.index == 5:
        await update_candidate_info(interaction, self.election, self.bot, self.vote_db)
    ## withdraw candidacy
    if self.index == 6:
        await withdraw_election(interaction, self.bot, self.vote_db)

async def position_selection_callback(self, interaction: discord.Interaction) -> None:
    await self.menu_message.edit_original_response(view=None)
    ## if they choose cancel
    if self.value.lower() == "cancel":
        return await self.menu_message.edit_original_response(content=f"Cancelled menu.", view=None, embed=None)
    
    for position in self.election['open_positions']:
        if position['title'].lower() == self.value.lower():
            position_slug = position['slug']
    

    await interaction.response.send_modal(Add_User_Info_Modal(self.bot, self.vote_db, position_slug=position_slug))

async def position_dropdown_callback(self, interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    candidate_list = self.storage
    candidate_selection = self.values
    candidate_selection = candidate_selection[0]

    for candidate in candidate_list:
        if candidate_selection == candidate['string']:
            ## cast vote and update voters in election
            await self.vote_db.add_vote_to_candidate(interaction.guild.id, interaction.user.id, candidate['id'])
            ## update user vote
            #await self.vote_db.store_user_votes(interaction.guild.id, interaction.user.id, candidate['id'], candidate['position_title'], candidate['position_slug'])

    #await interaction.edit_original_response(view=None)
    await interaction.delete_original_response()
    
