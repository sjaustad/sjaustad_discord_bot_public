import discord, traceback
from discord import app_commands
from discord.ext import commands
from datetime import datetime
from settings.server_settings import settings
settings = settings()

class FeedBack_cog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="feedback", description="Submit bugs or general feedback")
    async def command(self, interaction: discord.Interaction):
        await interaction.response.send_modal(feedback_modal(self.bot))
    
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(FeedBack_cog(bot))


class feedback_modal(discord.ui.Modal, title="Feedback"):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
    ## turns out Discord doesn't support this yet
    # select_options = [
    #     discord.SelectOption(label='Bug report'),
    #     discord.SelectOption(label='Suggestion'),
    #     discord.SelectOption(label='Complaint'),
    #     discord.SelectOption(label='Praise')
    # ]

    #select_ui = discord.ui.Select(options=select_options)
    category = discord.ui.TextInput(
        label='Feedback Category',
        placeholder="Bug, Suggestion, Complaint, Praise",

    )    

    comments = discord.ui.TextInput(
        label='Comments',
        style=discord.TextStyle.long,
        placeholder="If you're reporting a bug, please include the command used and the steps to reproduce the error.",
        required=False,
        max_length=600,
    )
    

    async def on_submit(self, interaction: discord.Interaction):

        

        ## send feedback
        feedback_channel = self.bot.get_channel(getattr(settings.guilds,str(interaction.guild.id)).server.channels.feedback_channel)
        
        feedback_embed = discord.Embed(title="New feedback received!", description=f"{feedback_channel.mention}")
        feedback_embed.add_field(name="From",value=f"{interaction.user.mention}")
        feedback_embed.add_field(name="Category",value=self.category.value)
        feedback_embed.add_field(name="Time",value=f"{datetime.now().strftime('%m/%d/%y %I:%M%p')}")
        feedback_embed.add_field(name="Comments",value=self.comments.value, inline=False)
        await interaction.response.send_message(f'Thanks for your feedback, {interaction.user.mention}!', ephemeral=True)
        await feedback_channel.send(embed=feedback_embed)

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        try:
            await interaction.response.send_message('Oops this is embarassing! Something went wrong. Contact bot owner.', ephemeral=True)
        except discord.errors.InteractionResponded:
            await interaction.followup.send(content='Oops this is embarassing! Something went wrong. Contact bot owner.', ephemeral=True)

        # Make sure we know what the error actually is
        traceback.print_tb(error.__traceback__)