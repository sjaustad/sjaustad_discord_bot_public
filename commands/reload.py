import discord, traceback
from discord import app_commands
from discord.ext import commands
from settings.server_settings import settings
settings=settings()
## Role Auth import
from utils.auth.check_role import CheckRole
auth = CheckRole()


class Reload_cog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="reload", description="Reload a cog")
    #@app_commands.checks.has_any_role(settings.discord.perms.superadminrole, settings.discord.perms.sudorole, settings.discord.perms.operatorrolename)
    async def reload(self, interaction: discord.Interaction, extension: str):
        if not auth.check_role(settings, interaction.guild, interaction.user, ['superadmin', 'sudo','operator']): return await auth.not_auth_message(interaction=interaction)

        ## reload the cog:
        try:
            await self.bot.reload_extension(extension)
            await interaction.response.send_message(f"{extension} reloaded", ephemeral=True)
        except:
            await interaction.response.send_message(f"{extension} failed to reload", ephemeral=True)

    @reload.autocomplete('extension')
    async def extension_autocomplete(self, interaction: discord.Interaction, current:str) -> list[app_commands.Choice[str]]:
        #extension_list = self.bot.extensions.keys()
        extension_list = [i for i in self.bot.extensions.keys()]
        return [
            app_commands.Choice(name=extension, value=extension)
            for extension in extension_list if current.lower() in extension.lower()
        ]

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Reload_cog(bot))