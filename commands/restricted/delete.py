import discord, traceback
from discord import app_commands
from discord.ext import commands

from settings.server_settings import settings
settings = settings()

## Role Auth import
from utils.auth.check_role import CheckRole
auth = CheckRole()


class Delete_cog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
    
    @app_commands.command(name="delete", description="deletes specified quantity of messages")
    #@app_commands.checks.has_any_role(settings.discord.perms.adminrolename, settings.discord.perms.superadminrole, settings.discord.perms.sudorole, settings.discord.perms.postmod)
    async def delete(self, interaction: discord.Interaction, quantity: int, user: discord.User = None):
        if not auth.check_role(settings, interaction.guild, interaction.user, ['superadmin', 'sudo', 'postmod','admin']): return await auth.not_auth_message(interaction=interaction)

        await interaction.response.send_message(f"Deleting {quantity} messages")
        quantity +=1
        if quantity > 100:
            await interaction.edit_original_response(content=f"Can't delete more than 100 messages at a time, deleting 100...")
            quantity = 100
        elif quantity <= 0: return

        if user is None:
            await delete_channel_messages(interaction.channel, quantity)
        else:
            await delete_user_messages(interaction.channel, quantity, user)
        try:
            await interaction.delete_original_response()
        except:
            pass ## already deleted.. probably

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Delete_cog(bot))


async def delete_channel_messages(channel, quantity):
    return await channel.purge(limit=quantity)

async def delete_user_messages(channel, quantity, user):

    user_messages = []
    async for message in channel.history(limit=100):
        if message.author == user:
            user_messages.append(message)

    for x in range (0,quantity-1):
        await user_messages[x].delete()