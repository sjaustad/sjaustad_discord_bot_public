from code import interact
import discord, asyncio
from discord import app_commands
from discord.ext import commands
from discord.utils import get

from settings.server_settings import settings
settings = settings()

## Role Auth import
from utils.auth.check_role import CheckRole
auth = CheckRole()


class Sudo_cog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
    
    @app_commands.command(name="sudo", description="grants sudo access to server")
    #@app_commands.checks.has_any_role(settings.discord.perms.superadminrole, settings.discord.perms.sudorole)
    async def sudo(self, interaction: discord.Interaction):
        if not auth.check_role(settings, interaction.guild, interaction.user, ['superadmin', 'sudo']): return await auth.not_auth_message(interaction=interaction)

        sudo_minutes = 15

        guild_roles = getattr(settings.guilds, str(interaction.guild_id)).server.roles
        role = get(interaction.guild.roles, name=guild_roles.sudo)

        await interaction.user.add_roles(role)
        await interaction.response.send_message(f"{interaction.user.mention}, you have authorized sudo for {sudo_minutes} minutes.", ephemeral=True)
        await asyncio.sleep(sudo_minutes * 60)
        await interaction.user.remove_roles(role)
        try:
            await interaction.edit_original_response(f"{interaction.user.mention}, sudo access finished. Returning user to normal status")
        except:
            pass ## already removed

    @app_commands.command(name="unsudo", description="removes your sudo access to the server")
    #@app_commands.checks.has_any_role(settings.discord.perms.superadminrole, settings.discord.perms.sudorole)
    async def unsudo(self, interaction: discord.Interaction):
        if not auth.check_role(settings, interaction.guild, interaction.user, ['superadmin', 'sudo']): return await auth.not_auth_message(interaction=interaction)
        
        guild_roles = getattr(settings.guilds, str(interaction.guild_id)).server.roles
        role = get(interaction.guild.roles, name=guild_roles.sudo)
        await interaction.user.remove_roles(role)
        await interaction.response.send_message(f"{interaction.user.mention} sudo access revoked.", ephemeral=True)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Sudo_cog(bot))


