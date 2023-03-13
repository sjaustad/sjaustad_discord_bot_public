from code import interact
from http import server
import discord, traceback, asyncio
from discord import app_commands
from discord.ext import commands

from utils.views.button_menu import InteractionMenu
from utils.database.calls.server import Server

mute_time = 300 # 5 minutes in seconds
vote_margin = 0.60 # percentage to allow a mute
vote_wait_time = 20 # seconds to wait before counting votes
vote_minimum = 3 # at least three votes have to be cast

class Mute_cog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.server = Server(bot.redis)

    @app_commands.command(name="mute", description="Vote to mute a person in a voice channel.")
    async def mute(self, interaction: discord.Interaction, user:discord.User):
        
        target_user = user

        if target_user.id == self.bot.application_id:
            await interaction.response.send_message(f"{interaction.user.mention}, you've been muted for 60 seconds!")
            await interaction.user.edit(mute=True)
            await asyncio.sleep(60)
            await interaction.user.edit(mute=False)
            return


        ## Make sure user is in a voice channel
        try:
            voice_channel_requester = interaction.user.voice.channel
        except:
            return await interaction.response.send_message(f"{interaction.user.mention}, you need to be in a voice channel to mute someone.", ephemeral=True)

        # Make sure target user is in a voice channel
        try:
            voice_channel_target = target_user.voice.channel
        except:
            return await interaction.response.send_message(f"{interaction.user.mention}, the target user needs to be in a voice channel.", ephemeral=True)

        

        await self.server.set_attribute(f'{interaction.guild_id}.mute_vote_approve:{interaction.id}',0)
        await self.server.set_attribute(f'{interaction.guild_id}.mute_vote_deny:{interaction.id}',0)

        ## Only allow people in a voice channel to do the voting
        voting_list = voice_channel_requester.voice_states.keys()
        voting_list = list(voting_list)
        eligible_voters=[]
        for user in voting_list:
            eligible_voters.append(await self.bot.fetch_user(user))



        options = ['yes','no']

        embed = discord.Embed(title=f"{interaction.user.name} has started a vote to mute {target_user.name} for 5 minutes", description="Do you vote to mute them?")

        ## instantiate menu class
        menu = InteractionMenu(self.bot)
        
        
        ## define the call back for the custom_button
        ## see below for async callback
        menu.custom_button.callback = callback
        ## set other custom attributes for buttons:
        menu.custom_button.voters = eligible_voters
        menu.custom_button.interaction_id = interaction.id
        menu.custom_button.server = self.server
        menu.custom_button.target_user = target_user

        ## Generate the menu view with the buttons
        menu_view = await menu.generate_view(options, interaction=interaction, cancel_button=False)
        ## Send the menu message
        await interaction.response.send_message(view=menu_view, embed=embed)

        ## wait a certain amount of time
        await asyncio.sleep(vote_wait_time)

        ## clean up vote
        await interaction.edit_original_response(view=None)

        approvals = await self.server.get_attribute(f'{interaction.guild_id}.mute_vote_approve:{interaction.id}')
        denials = await self.server.get_attribute(f'{interaction.guild_id}.mute_vote_deny:{interaction.id}')
        #print(approvals)
        #print(denials)


        vote_pass = False
        ## didn't get enough votes at all
        if (approvals + denials) < vote_minimum: 
            reason = f"Failed to reach needed amount of votes: {vote_minimum}. Total votes: {approvals + denials}"
            
        ## sufficient number of approvals
        elif (approvals > denials):
            ## automatic pass if no denials and already passed margin above
            if denials != 0:
                ## make sure denials is above threshold
                if (approvals/denials) > vote_margin:
                    
                    vote_pass = True
                ## otherwise fails on margin
                else:
                    reason = f"Failed to reach threshold of {round(vote_margin*100)}%: {approvals} approved to {denials} denied"
            ## vote passed if no denials
            else:
                
                vote_pass = True
        ## approvals didn't beat out denials
        else:
            
            reason = f"Failed to reach enough approvals: {approvals} approved to {denials} denied"

        if vote_pass is True:
            reason = f"Vote to mute {target_user.name} passed!"
            try:
                await target_user.edit(mute=True)
            except:
                pass ## user left voice already

        mute_results_embed = discord.Embed(title=f"Mute vote results for {target_user.name}", description=reason)
        await interaction.edit_original_response(embed=mute_results_embed)
        
        ## if you are not sending an interaction, but rather a regular message and you want
        ## to be able to edit the original message inside the callback, you will need to add
        ## the message to each button with this method.
        #menu.allow_original_menu_updates(menu_view, menu_message)

        await self.server.remove_attribute(f'mute_vote_approve:{interaction.id}')
        await self.server.remove_attribute(f'mute_vote_deny:{interaction.id}')

        await asyncio.sleep(mute_time)
        try:
            await target_user.edit(mute=False)
        except:
            pass ## already unmuted or left voice channel

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Mute_cog(bot))


async def callback(self, interaction: discord.Interaction) -> None:

    ## if they choose cancel
    #if self.value.lower() == "cancel":
    #    return await self.menu_message.edit_original_response(content=f"Cancelled menu.", view=None, embed=None)
    
    ## are they allowed to vote?
    ## they must be in a voice channel
    found = False
    for voter in self.voters:
        if voter == interaction.user:
            found = True
            break

    if found is False:
        return await interaction.response.send_message(f'{interaction.user.mention} you need to have been in a voice channel at the start of this vote!', ephemeral=True) 

    if self.value == 'yes':
        await self.server.increment(f'mute_vote_approve:{self.interaction_id}')
    elif self.value == 'no':
        await self.server.increment(f'mute_vote_deny:{self.interaction_id}')

    ## console log choice
    #print(f"You chose {self.value}!")
    ## create new embed
    #new_embed = discord.Embed(title=f"You selected {self.value} at menu index {self.index}")
    ## remove the options and send new embed to original message
    #await self.menu_message.edit_original_response(view=None, embed=new_embed)
    await interaction.response.send_message(f"You voted {self.value} to muting {self.target_user.name}.",ephemeral=True)
    ## if the original message sent is not ephemeral (user only) you can delete it, otherwise you cannot
    #await self.menu_message.delete_original_response()