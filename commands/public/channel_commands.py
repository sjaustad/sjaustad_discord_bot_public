from code import interact
from distutils.command.config import config
import discord, traceback, datetime
from discord import app_commands
from discord.ext import commands


from utils.views.confirm import Confirm
from settings.server_settings import settings
settings=settings()

from utils.database.calls.users import Users

class Channel_cog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        
        self.users=Users(bot.redis)
        
    @app_commands.command(name="channel", description="Create 24 hour temporary voice channels")
    async def channel(self, interaction: discord.Interaction, voice_channel_name: str):


        ## Make sure there isn't already a voice channel with that name
        existing_channel = discord.utils.find(lambda c: c.name == voice_channel_name and c.type.name == 'voice', interaction.channel.guild.voice_channels)
        if existing_channel is not None: return await interaction.response.send_message(f"{interaction.user.mention} a voice channel with this name already exists!", ephemeral=True)

        ## Check to see if the user has a voice channel already, offer to delete it
        current_user_channel = await self.users.get_attribute(interaction.user.id, "voice_channel")
        await interaction.response.defer(ephemeral=True)
        if current_user_channel is not None:
            user_response = await Confirm.display(interaction=interaction,text=f"You currently have registered the voice channel named: {current_user_channel['name']}. Do you wish to remove it and create a new one?",cancel_text="No changes made.")
            if user_response is None: return
            elif user_response:
                await interaction.edit_original_response(content='Removing old channel and creating new one.')
                thisChannel = self.bot.get_channel(current_user_channel['channelid'])
                try:
                    await thisChannel.delete()
                except:
                    pass
                await self.users.remove_attribute(interaction.user.id, "voice_channel")
            else: return

                #voice_channel_name = await getChannelName(ctx)
                #if voice_channel_name is None: return

        ## Get voice channel category
        ## current_guild = await ctx.bot.get_guild(settings.discord.guildid)
        voice_category = self.bot.get_channel(getattr(settings.guilds,str(interaction.guild.id)).server.settings.voice_channel_category_example).category


        ## Create a new voice channel
        try:
            new_channel = await interaction.channel.guild.create_voice_channel(voice_channel_name, category = voice_category)
        except Exception as e:
            print(e)
            return await interaction.edit_original_response(content=f"{interaction.user.mention} Failed to create voice channel.")
        channel_data = {
            'userid':interaction.user.id,
            'name':voice_channel_name,
            'created':datetime.datetime.now().strftime('%m/%d/%y %I:%M%p'),
            'channelid':new_channel.id
        }
        await self.users.set_attribute(interaction.user.id, "voice_channel", channel_data)
        return await interaction.edit_original_response(content=f"{interaction.user.mention} successfully created new voice channel {voice_channel_name}.")
    
    @app_commands.command(name="unchannel", description="Remove your current temporary voice channel")
    async def unchannel(self, interaction: discord.Interaction):
        #await ctx.message.delete()
        ## Check to see if the user has a voice channel already, offer to delete it
        current_user_channel = await self.users.get_attribute(interaction.user.id, "voice_channel")
        if current_user_channel is not None:
            thisChannel = self.bot.get_channel(current_user_channel['channelid'])
            await thisChannel.delete()
            await self.users.remove_attribute(interaction.user.id, "voice_channel")
            return await interaction.response.send_message(f"{interaction.user.mention} voice channel **{current_user_channel['name']}** has been removed.", ephemeral=True)

        else:
            return await interaction.response.send_message(f"{interaction.user.mention} no voice channel registered to you.",ephemeral=True)
    
    
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Channel_cog(bot))
