import discord, traceback
from discord import app_commands
from discord.ext import commands

## Settings needed to get server roles
from settings.server_settings import settings
settings = settings()

## Role Auth import
from utils.auth.check_role import CheckRole
auth = CheckRole()


class AuthCommandName_cog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="authorized_command", description="<description>")
    ## additional variables in the command function will become options in the slash command
    ## e.g.: async def say(self, interaction: discord.Interaction, text_to_speech: str):
    ## When using /say this commadn will now have an option for text_to_speech as a string input
    async def command(self, interaction: discord.Interaction):
        ## Basic send message:
        # await interaction.response.send_message(f'Hi, {interaction.user.mention}')
        ## You may want to defer an action if it's going to take a minute to get the user a response otherwise the reponse will faile
        # await interaction.response.defer(ephemeral=True)
        ## After sending any response, you can only use followup, you cannot send another response
        # await interaction.followup.send('message')

        ## authorized roles can be as long as needed or as short as one role
        authorized_roles = ['superadmin', 'sudo']
        if not auth.check_role(settings, interaction.guild, interaction.user, authorized_roles): return await auth.not_auth_message(interaction=interaction)

    
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AuthCommandName_cog(bot))