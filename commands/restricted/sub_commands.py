from code import interact
from dis import disco
from doctest import debug_script
from operator import truediv
import discord, traceback
from discord import app_commands
from discord.ext import commands


from utils.views.dropdown import DropdownMenu
from utils.database.calls.server import Server
from utils.views.confirm import Confirm

import string, random,datetime,dateutil

from settings.server_settings import settings
settings = settings()

## Role Auth import
from utils.auth.check_role import CheckRole
auth = CheckRole()



class Sub_cog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.server = Server(bot.redis)
   

    @app_commands.command(name="unsub", description="Unsubscribe from text channels.")
    ## additional variables in the command function will become options in the slash command
    ## e.g.: async def say(self, interaction: discord.Interaction, text_to_speech: str):
    ## When using /say this commadn will now have an option for text_to_speech as a string input
    async def unsub(self, interaction: discord.Interaction):
       
        ## Get sub list
        sub_channels = await self.server.index_search(f"{interaction.guild_id}.sub_channel")

        if len(sub_channels) <= 0: return await interaction.response.send_message("There are no subscribable channels on this server", ephemeral=True)
        await interaction.response.defer(ephemeral=True)

        user_subs = []
 
        for text_channel in sub_channels:
            try:
                thisChannel = self.bot.get_channel(text_channel['value']['channel_id'])
                if thisChannel is None: continue
                overwrite = thisChannel.overwrites_for(interaction.user)
                if overwrite.read_messages is True and overwrite.send_messages is True:
                    user_subs.append(discord.SelectOption(label=text_channel['value']['name']))
            except:
                continue
        
        if len(user_subs) <= 0: return await interaction.followup.send(f"You don't have any channels you are subscribed to!", ephemeral=True)
        await DropdownMenu.display(interaction, user_subs, "Select channels you would like to sub to",bot=self.bot ,min_values=1, max_values=len(user_subs))
        
        async def callback(self, interaction: discord.Interaction):
            unsub_requests = self.values

            processed_all = True
            for request in unsub_requests:
                thisChannel = [x for x in sub_channels if x['value']['name'] == request][0]
                permission_channel = self.bot.get_channel(thisChannel['value']['channel_id'])
                success = await remove_channel_permission(interaction, permission_channel)
                if success is False: processed_all=False           

            if processed_all is True:
                await interaction.response.send_message(f"Processed all of your unsubs successfully.", ephemeral=True)
            else:
                await interaction.response.send_message(f"Failed to process all of your unsubs", ephemeral=True)
            await interaction.edit_original_response(view=None)

        DropdownMenu.ui.callback = callback

    @app_commands.command(name="sub", description="Subscribe to text channels which are normally hidden.")
    ## additional variables in the command function will become options in the slash command
    ## e.g.: async def say(self, interaction: discord.Interaction, text_to_speech: str):
    ## When using /say this commadn will now have an option for text_to_speech as a string input
    async def sub(self, interaction: discord.Interaction, code:str = None):
        await interaction.response.defer(ephemeral=True)
        ## Get sub list
        sub_channels = await self.server.index_search(f"{interaction.guild_id}.sub_channel")
        if len(sub_channels) <= 0: return await interaction.edit_original_response(content="There are no subscribable channels on this server.")
        elevated = auth.check_role(settings, interaction.guild, interaction.user, ['superadmin', 'sudo'])



        if code is not None:
            info = await self.server.get_attribute(f"{interaction.guild_id}.codes.{code}")
            if info is None: return await interaction.edit_original_response(content=f"{interaction.user.mention}, this code is invalid.")
            else:
                ## check time
                time_diff = datetime.datetime.now() - dateutil.parser.parse(info['creation'])
                if time_diff.days > 0: 
                    await interaction.edit_original_response(content=f"{interaction.user.mention}, this code has expired.")
                    return await self.server.remove_attribute(f"{interaction.guild_id}.codes.{code}")
                else:
                    permission_channel = self.bot.get_channel(info['channel_id'])
                    await add_channel_permission(interaction, permission_channel)
                    return await self.server.remove_attribute(f"{interaction.guild_id}.codes.{code}")

        ## Generate list of subs
        sub_list = []
        for sub in sub_channels:
            if not 'secret' in sub['value']: continue
            if sub['value']['secret'] is False:
                sub_list.append(discord.SelectOption(label=sub['value']['name']))
            elif elevated is True:
                sub_list.append(discord.SelectOption(label=sub['value']['name']))
            
        ## if there are subs but only hidden ones
        if len(sub_list) < 1: return await interaction.edit_original_response(content=f"There are no subscribable channels on this server.")
            
        
        
        await DropdownMenu.display(interaction, sub_list, "Select channels you would like to sub to",bot=self.bot ,min_values=1, max_values=len(sub_list))
        
        async def callback(self, interaction: discord.Interaction):
            sub_requests = self.values

            for request in sub_requests:
                thisChannel = [x for x in sub_channels if x['value']['name'] == request][0]
                permission_channel = self.bot.get_channel(thisChannel['value']['channel_id'])
                await add_channel_permission(interaction, permission_channel)
            await interaction.edit_original_response(view=None)

        DropdownMenu.ui.callback = callback

class Subadmin_cog(commands.GroupCog, name="editsub"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.server = Server(bot.redis)
    @app_commands.command(name="add", description="Add subbable channels.")
    #@app_commands.checks.has_any_role(settings.discord.perms.adminrolename, settings.discord.perms.superadminrole, settings.discord.perms.sudorole)
    async def add(self, interaction: discord.Interaction, channel_id: str, description: str, secret:bool=False) -> None:
        if not auth.check_role(settings, interaction.guild, interaction.user, ['superadmin', 'sudo', 'admin']): return await auth.not_auth_message(interaction=interaction)

        try:
            channel_id = int(channel_id)
        except: return

        ## verify the channel is real
        channel = self.bot.get_channel(channel_id)
        if channel is None: return await interaction.response.send_message(f"I couldn't find a channel with the id {channel_id} in this server.", ephemeral=True)

        await add_new_sub_channel(self.bot, interaction, channel, channel_id, description, secret)

    @app_commands.command(name="remove", description="Remove subbable channels.")
    #@app_commands.checks.has_any_role(settings.discord.perms.adminrolename, settings.discord.perms.superadminrole, settings.discord.perms.sudorole)
    async def remove(self, interaction: discord.Interaction) -> None:
        
        if not auth.check_role(settings, interaction.guild, interaction.user, ['superadmin', 'sudo','admin']): return await auth.not_auth_message(interaction=interaction)

        await interaction.response.defer(ephemeral=True)
        ## Get sub list
        sub_channels = await self.server.index_search(f"{interaction.guild_id}.sub_channel")
        if len(sub_channels) <= 0: return await interaction.edit_original_response(content="There are no subscribable channels on this server")

        ## Generate list of subs
        sub_list = []
        for sub in sub_channels:
            sub_list.append(discord.SelectOption(label=sub['value']['name']))
        
        await DropdownMenu.display(interaction, sub_list, "Select channels you would like to remove as subbable channels",bot=self.bot ,min_values=1, max_values=len(sub_list))

        async def callback(self, interaction: discord.Interaction):

            user_response = await Confirm.display(interaction=interaction,text=f"Would you also like to delete the selected channels?",cancel_text="Channels are not deleted, but no longer subscribable.", confirm_button_text="Yes", cancel_button_text = "No")
            if user_response is None: return
            elif user_response:
                delete_channels = True
            else: delete_channels = False

            sub_requests = self.values
            for request in sub_requests:
                thisChannel = [x for x in sub_channels if x['value']['name'] == request][0]
                discord_channel = interaction.channel.guild.get_channel(thisChannel['value']['channel_id'])
                await remove_sub_channel(interaction, discord_channel, delete_channels, self.bot)

        DropdownMenu.ui.callback = callback


    @app_commands.command(name="generate_code", description="Generate codes for channels.")
    #@app_commands.checks.has_any_role(settings.discord.perms.adminrolename, settings.discord.perms.superadminrole, settings.discord.perms.sudorole)
    async def generate_code(self, interaction: discord.Interaction) -> None:
        
        if not auth.check_role(settings, interaction.guild, interaction.user, ['superadmin', 'sudo']): return await auth.not_auth_message(interaction=interaction)

        await interaction.response.defer(ephemeral=True)
        ## Get sub list
        sub_channels = await self.server.index_search(f"{interaction.guild_id}.sub_channel")
        if len(sub_channels) <= 0: return await interaction.edit_original_response(content="There are no subscribable channels on this server")

        ## Generate list of subs
        sub_list = []
        for sub in sub_channels:
            sub_list.append(discord.SelectOption(label=sub['value']['name']))
        
        await DropdownMenu.display(interaction, sub_list, "Select channels you would like to generate codes",bot=self.bot ,min_values=1, max_values=len(sub_list))

        async def callback(self, interaction: discord.Interaction):

            sub_requests = self.values
            codes = ""
            for request in sub_requests:
                thisChannel = [x for x in sub_channels if x['value']['name'] == request][0]
                discord_channel = interaction.channel.guild.get_channel(thisChannel['value']['channel_id'])
                code = ''.join(random.choices(string.ascii_lowercase, k=25))
                info = {
                    'channel_id':discord_channel.id,
                    'creation':datetime.datetime.now()
                }
                await self.server.set_attribute(f"{interaction.guild_id}.codes.{code}",info)
                codes += f"{discord_channel.name} | {code}\n"
            
            await interaction.response.send_message(codes,ephemeral=True)

        DropdownMenu.ui.callback = callback
        DropdownMenu.ui.server = self.server


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Sub_cog(bot))
    await bot.add_cog(Subadmin_cog(bot))

async def add_channel_permission(interaction, channel):
    try:
        await interaction.response.defer(ephemeral=True)
    except:
        pass
    try:
        await channel.set_permissions(interaction.user, read_messages=True, send_messages=True)
    except:
        return await interaction.edit_original_response(content=f"{interaction.user.mention} an error occurred adding you to this channel. Please let someone know.")
    await interaction.edit_original_response(content=f"{interaction.user.mention} you have been added to the channel {channel.name} ")

async def remove_channel_permission(interaction, permission_channel):
    result = True
    try:
        await permission_channel.set_permissions(interaction.user, read_messages=False, send_messages=False)
    except:
        result = False
        await interaction.response.send_message(f"{interaction.user.mention} an error occurred removing you from this channel. Please let someone know.")
    return result


async def add_new_sub_channel(bot, interaction:discord.Interaction, channel, channel_id, description, secret):
    ## verify the channel is not already in the sub list
    server = Server(bot.redis)
    current_sub_channels = await server.index_search(f"{interaction.guild_id}.sub_channel")
    if current_sub_channels is not None:
        for chan in current_sub_channels:
            if chan['value']['channel_id'] == channel_id: return await interaction.response.send_message(f"This channel is already a subscription based channel!")

    channel_dict = {
        'name':channel.name,
        'channel_id':channel.id,
        'guild_id':interaction.guild_id,
        'secret':secret
    }

    await server.set_attribute(f"{interaction.guild_id}.sub_channel.{channel.name}", channel_dict)

    ## Edit perms
    try:
        await channel.set_permissions(interaction.channel.guild.default_role, send_messages=False, read_messages=False)
    except Exception as e:
        print(f"Problem changing channel permissions: {e}")
    
    if description is not None:
        await server.set_attribute(f"{interaction.guild_id}.sub_channel.{channel.name}.description",description, index=False)

    #updateAttribute(ctx.bot.user, "sub_channel", sub_channel_dict)

    await interaction.response.send_message(f"{channel.name} has been added as subscribable channel.", ephemeral=True)


async def remove_sub_channel(interaction, channel, delete_channels, bot):
    server = Server(bot.redis)
    channel_id = channel.id
    ## verify the channel is not already in the sub list
    current_sub_channels = await server.index_search(f"{interaction.guild_id}.sub_channel")
    found = False
    if current_sub_channels is not False:
        for chan in current_sub_channels:
            if chan['value']['channel_id'] == channel_id: 
                found = True
    if found is False: return await interaction.response.send_message(f"This channel is not currently a subscription based channel!", ephemeral=True)

    await server.remove_attribute(f"{interaction.guild_id}.sub_channel.{channel.name}")
    if delete_channels is True:
       
        await channel.delete()
        await interaction.followup.send(f"{channel.name} has been removed as subscribable channel and deleted.", ephemeral=True)
    else:
        await interaction.followup.send(f"{channel.name} has been removed as subscribable channel.", ephemeral=True)
    #removeSingleUserAttribute("sub_channel", channel.name)
    
