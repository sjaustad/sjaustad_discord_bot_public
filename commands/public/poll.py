from typing import Counter
import discord, traceback
from discord import app_commands
from discord.ext import commands
from utils.database.calls.polls import Polls

class Poll_cog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="poll", description="Create a poll to get other people's opinion.")
    async def poll(self, interaction: discord.Interaction):
        await interaction.response.send_modal(poll_modal(self.bot))
        pass
    
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Poll_cog(bot))



class poll_modal(discord.ui.Modal, title="Poll Creation"):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.poll_db = Polls(self.bot.redis)

    name = discord.ui.TextInput(
        label='Poll Name',
        placeholder="What do you want to the poll to be called?",

    )    

    options = discord.ui.TextInput(
        label='Poll options',
        style=discord.TextStyle.long,
        placeholder="Enter each option on a new line. e.g.:\n1. pepperoni\n2.mushrooms\n3.olives",
        required=False,
        max_length=600,
    )
    

    async def on_submit(self, interaction: discord.Interaction):

        await interaction.response.send_message(f'Creating poll, {interaction.user.mention}!', ephemeral=True)

        ## generate options
        options_text = self.options.value
        options_list = options_text.splitlines()

        ## generate view
        poll_view = poll_options()

        ## add the button options
        for option in options_list:
            poll_view.add_item(Btn(option, self.poll_db))

        ## make an embed
        poll_embed = discord.Embed(title=self.name.value,description=f"Respond to this poll created by {interaction.user.mention}!")

        ## move cancel button to the last option of list
        poll_view.children.append(poll_view.children.pop(0))

        ## send view and embed 
        poll = await interaction.followup.send(view=poll_view, embed=poll_embed)

        ## store the new interaction information
        poll_view.og_interaction = poll
        poll_view.og_user = interaction.user

        ## store poll in DB
        await self.poll_db.initial_poll_store(poll.id, interaction.user, options_list)

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await interaction.followup.send('Failed to create poll.', ephemeral=True)

        # Make sure we know what the error actually is
        traceback.print_tb(error.__traceback__)


class poll_options(discord.ui.View):
    def __init__(self,):
        super().__init__()
        self.value = None
        self.og_user = None #og_interaction.user
        self.og_interaction = None #og_interaction

    # This one is similar to the confirmation button except sets the inner value to `False`
    @discord.ui.button(label='Cancel', style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        #await interaction.response.send_message(self.cancel_text, ephemeral=True)
        if interaction.user == self.og_user:
            self.value = False
            self.stop()
            try:
                await self.og_interaction.delete()
            except:
                return await interaction.response.send_message("Failed to delete poll.", ephemeral=True)
    
            await interaction.response.send_message("Poll deleted", ephemeral=True)
        else:
            await interaction.response.send_message("Only the poll owner can delete this poll.", ephemeral=True)

class Btn(discord.ui.Button):
    def __init__(self, label, poll_db):
        super().__init__()
        self.value = label
        self.label = label
        self.poll_db = poll_db
        self.style = discord.ButtonStyle.grey


    ## callback function for user results
    async def callback(self, interaction: discord.Interaction) -> None:
        skip_db_entry = False
        if self.value == "refresh":
            skip_db_entry = True

        if skip_db_entry is False:
            
            await interaction.response.defer(ephemeral=True)
            ## check if allowed to vote again
            poll = await self.poll_db.get_poll_results(interaction.message.id)
            store = True
            for result in poll['results']:
                if result['id'] == interaction.user.id:
                    result_index = poll['results'].index(result)
                    poll['results'].pop(result_index)
                    await self.poll_db.update_poll(poll)
                    store=True
                    #await interaction.edit_original_response(content="You've already responded to this poll!")
                    await interaction.followup.send("Your response has been updated.", ephemeral=True)

            
            ## store result in DB
            if store is True:
                await self.poll_db.store_poll_entry(interaction.message.id, interaction.user, self.value)

        ## display results
        results_embed = discord.Embed(title="Results",description="Results for poll")
        poll = await self.poll_db.get_poll_results(interaction.message.id)
        results_text = ""
        items = Counter(result['option'] for result in poll['results'])

        x=1
        for item in items:
           
            count=items[item]
            results_text += f"{x}. {item} - {count}\n"
            x+=1
        results_embed.add_field(name="Stats", value=results_text)

        poll_results_view = poll_results(poll['poll_id'], self.poll_db, og_interaction=interaction)
        new_interaction = await interaction.followup.send(embed=results_embed, ephemeral=True, view=poll_results_view)
        poll_results_view.og_interaction = new_interaction

class poll_results(discord.ui.View):
    def __init__(self, poll_id, poll_db, og_interaction=None):
        super().__init__()
        self.value = None
        self.og_interaction = None
        self.poll_db = poll_db
        self.poll_id = poll_id

    # This one is similar to the confirmation button except sets the inner value to `False`
    @discord.ui.button(label='↻', style=discord.ButtonStyle.grey)
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        #await interaction.response.send_message(self.cancel_text, ephemeral=True)
        self.value = 'refresh'

        ## display results
        results_embed = discord.Embed(title="Results",description="Results for poll")
        poll = await self.poll_db.get_poll_results(self.poll_id)
        results_text = ""
        items = Counter(result['option'] for result in poll['results'])

        x=1
        for item in items:
           
            count=items[item]
            results_text += f"{x}. {item} - {count}\n"
            x+=1
        results_embed.add_field(name="Stats", value=results_text)

        await self.og_interaction.edit(embed=results_embed)
