from code import interact
import math, asyncio
from multiprocessing.connection import wait
import queue
from time import sleep
import discord
from discord.ext import commands
from discord.utils import get
from discord import app_commands

from urllib.parse import urlparse
from plugins.audio_player.AudioPlayer import audio_controller

from utils.database.calls.music_history import MusicHistory
from utils.views.confirm import Confirm
from settings.server_settings import settings
settings = settings()

## Role Auth import
from utils.auth.check_role import CheckRole
auth = CheckRole()



class audio_cog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.audio = AudioFunctions()
        self.music_db = MusicHistory(bot.redis)
        self.queue_list = []

    ## ban a user from using the generator, requires highest priviledges
    @app_commands.command(name="music_ban_user", description="Bans a user from using the music player.")
    #@app_commands.checks.has_any_role(settings.discord.perms.superadminrole, settings.discord.perms.sudorole)
    async def ban_user(self, interaction: discord.Interaction, user: discord.User):
        if not auth.check_role(settings, interaction.guild, interaction.user, ['superadmin', 'sudo']): return await auth.not_auth_message(interaction=interaction)

        await self.music_db.add_to_ban_list(user.id)
        await interaction.response.send_message(f"{user.mention}, you have been banned from using music player!")
    ## unban a user from using the generator, requires highest priviledges
    @app_commands.command(name="music_unban_user", description="Unbans a user from the music player.")
    #@app_commands.checks.has_any_role(settings.discord.perms.superadminrole, settings.discord.perms.sudorole)
    async def unban_user(self, interaction: discord.Interaction, user: discord.User):
        if not auth.check_role(settings, interaction.guild, interaction.user, ['superadmin', 'sudo']): return await auth.not_auth_message(interaction=interaction)
        await self.music_db.remove_from_ban_list(user.id)
        await interaction.response.send_message(f"{user.mention}, your ban on using the music player has been lifted!")
    


    # @app_commands.command(name="pause")
    # async def pause(self, interaction: discord.Interaction):
    #     await self.audio.pause_playback(interaction, self.bot)
    # @app_commands.command(name="skip")
    # async def skip(self, interaction: discord.Interaction):
    #     await self.audio.skip_track(interaction, self.bot)
    @app_commands.command(name="stop", description="Stops playback of current media and clears the queue.")
    async def stop(self, interaction: discord.Interaction):
        await self.audio.stop_playback(interaction, self.bot)
    # @app_commands.command(name="resume")
    # async def resume(self, interaction: discord.Interaction):
    #     await self.audio.resume_playback(interaction, self.bot)
    # @app_commands.command(name="loop")
    # async def loop(self, interaction: discord.Interaction):
    #     await self.audio.loop_track(interaction, self.bot)

    @app_commands.command(name="mc", description="Displays media playback controls")
    async def media_playback_controls(self, interaction: discord.Interaction):
        queue_embed = await build_queue_embed(interaction, self.bot)
        if self.bot.audio_controller.voice is not None:
            control_view = AudioControls.generate_view(self.bot)
            await interaction.response.send_message(embed=queue_embed, ephemeral=True, view=control_view)
        else:
            await interaction.response.send_message(f"{interaction.user.mention}, no media is playing right now.",ephemeral=True)

    @app_commands.command(name="clear_music_history", description="Clears the music history list.")
    #@app_commands.checks.has_any_role(settings.discord.perms.superadminrole, settings.discord.perms.sudorole)

    async def clear_music_history(self, interaction: discord.Interaction):
        if not auth.check_role(settings, interaction.guild, interaction.user, ['superadmin', 'sudo']): return await auth.not_auth_message(interaction=interaction)

        try:
            await self.music_db.clear_history()
        except:
            await interaction.response.send_message(f"{interaction.user.mention} failed to clear music history.")
        
        await interaction.response.send_message(f"{interaction.user.mention} cleared music history.")
        
    @app_commands.command(name="queue", description="View the currently playing media and queue.")
    async def queue(self, interaction: discord.Interaction):
        queue_embed = await build_queue_embed(interaction, self.bot)
        
        if self.bot.audio_controller.voice is not None:
            control_view = AudioControls.generate_view(self.bot)
            await interaction.response.send_message(embed=queue_embed, ephemeral=True, view=control_view)
        else:
            await interaction.response.send_message(embed=queue_embed, ephemeral=True)






def convert_to_minutes(length):
    if length >= 60:
        minutes = math.floor(length / 60)
        seconds = length - (minutes * 60)
        if seconds < 10: seconds = f"0{seconds}"
        return f"{minutes}:{seconds}"
    else:
        return f"{length}s"

        
async def setup(bot):
    await bot.add_cog(audio_cog(bot))



class AudioControls:
    def generate_view(bot):
        controls_view = AudioControls.controls_view(bot)
        
        ## set pause color
        try:
            if bot.audio_controller.voice.is_paused():
                controls_view.children[1].label='▶️'
                controls_view.children[1].style=discord.ButtonStyle.green                
            else:
                controls_view.children[1].label='⏸️'
                controls_view.children[1].style=discord.ButtonStyle.grey            
        except:
            pass ## accept button defaults

        ## set loop color
        try:
            if bot.audio_controller.current_audio['loop'] is True:
                controls_view.children[3].style=discord.ButtonStyle.green
            else:
                controls_view.children[3].style=discord.ButtonStyle.grey
        except:
            pass ## accept button defaults

        ## set mute color
        try:
            if bot.audio_controller.muted is True:
                controls_view.children[6].style=discord.ButtonStyle.red
            else:
                controls_view.children[6].style=discord.ButtonStyle.grey
        except:
            pass ## accept button defaults
        return controls_view
            
    class controls_view(discord.ui.View):
        def __init__(self, bot):
            super().__init__()
            self.audio = AudioFunctions()
            self.bot = bot

        @discord.ui.button(label='🟥', style=discord.ButtonStyle.red, row=0)
        async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.edit_message(view=None)
            await self.audio.stop_playback(interaction, self.bot, button=True)


        @discord.ui.button(label='⏸️', style=discord.ButtonStyle.grey, row=0)
        async def pause(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.edit_message(view=self)
            await self.audio.pause_playback(interaction, self.bot, button=True)
            #await interaction.edit_original_response(view=self)

        @discord.ui.button(label='⏭️', style=discord.ButtonStyle.grey, row=0)
        async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
            ## respond to interaction with nothing...
            await interaction.response.edit_message(view=self)
            await self.audio.skip_track(interaction, self.bot, button=True)
        
        @discord.ui.button(label='➰ loop', style=discord.ButtonStyle.grey, row=0)
        async def loop(self, interaction: discord.Interaction, button: discord.ui.Button):
            
            ## respond to interaction with nothing...
            await interaction.response.edit_message(view=self)
            await self.audio.loop_track(interaction, self.bot, button=True)

        @discord.ui.button(label='🔈', style=discord.ButtonStyle.grey, row=1)
        async def volume_lower(self, interaction: discord.Interaction, button: discord.ui.Button):
            ## respond to interaction with nothing...
            await interaction.response.edit_message(view=self)
            await self.audio.lower_volume(interaction, self.bot)

        @discord.ui.button(label='🔊', style=discord.ButtonStyle.grey, row=1)
        async def volume_raise(self, interaction: discord.Interaction, button: discord.ui.Button):
            ## respond to interaction with nothing...
            await interaction.response.edit_message(view=self)
            await self.audio.raise_volume(interaction, self.bot)

        @discord.ui.button(label='🔇', style=discord.ButtonStyle.grey, row=1)
        async def volume_mute(self, interaction: discord.Interaction, button: discord.ui.Button):
            ## respond to interaction with nothing...
            await interaction.response.edit_message(view=self)
            await self.audio.mute_volume(interaction, self.bot)

        @discord.ui.button(label='↻ refresh', style=discord.ButtonStyle.grey, row=1)
        async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
            ## respond to interaction with nothing...
            await interaction.response.edit_message(view=self)
            ## refresh window
            await self.audio.refresh_window(interaction, self.bot)




        @discord.ui.button(label='History', style=discord.ButtonStyle.grey, row=2)
        async def history_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            ## respond to interaction with nothing...
            ## Update queue embed
            
            if check_if_history(interaction.message):
                queue_embed = await build_queue_embed(interaction, self.bot)
            else:
                queue_embed = await build_queue_embed(interaction, self.bot, display_history=True)
            await interaction.response.edit_message(embed=queue_embed)

## function to continue displaying history in embed if it was selected
def check_if_history(message: discord.Message):
    try:
        for embed in message.embeds:
            for field in embed.fields:
                if field.name.lower().find('latest 10 tracks') != -1:
                    return True
    except AttributeError:
        pass
    return False

class AudioFunctions:
    async def refresh_window(self, interaction: discord.Interaction, bot):
        ## Update queue embed
        if check_if_history(interaction.message):
            queue_embed = await build_queue_embed(interaction, bot, display_history=True)
        else:
            queue_embed = await build_queue_embed(interaction, bot)

        await interaction.edit_original_response(embed=queue_embed, view=AudioControls.generate_view(bot))

    async def mute_volume(self, interaction: discord.Interaction, bot):
        try:
            voice_client = get(bot.voice_clients, guild=interaction.guild)

            ## mutes volume if not muted
            if voice_client:
                if bot.audio_controller.muted is False:
                    await self.music_db.store_volume(bot.audio_controller.voice.source.volume)
                    bot.audio_controller.voice.source.volume = 0.0
                    bot.audio_controller.muted = True
                ## puts volume back if muted
                else:
                    bot.audio_controller.voice.source.volume = await self.music_db.get_volume()
                    bot.audio_controller.muted = False

        except:
            pass
        ## Update queue embed
        if check_if_history(interaction.message):
            queue_embed = await build_queue_embed(interaction, bot, display_history=True)
        else:
            queue_embed = await build_queue_embed(interaction, bot)

        await interaction.edit_original_response(embed=queue_embed, view=AudioControls.generate_view(bot))
        

    async def loop_track(self, interaction: discord.Interaction, bot, button=False):
        ## Get the author's voice channel and make sure they are in a voice channel
        try:
            voice_channel = interaction.user.voice.channel
        except:
            return await interaction.response.send_message(f"{interaction.user.mention}, you need to be in a voice channel to loop tracks.", ephemeral=True)
        
        ## Check to see if bot is currently playing something back
        if bot.audio_controller.voice is None:
            return await interaction.response.send_message(f"{interaction.user.mention}, I'm not currently playing anything.", ephemeral=True)
        try:
            
            if bot.audio_controller.current_audio['loop'] is False:
                bot.audio_controller.current_audio['loop'] = True
                if not button:
                    await interaction.response.send_message(f"Now looping {bot.audio_controller.current_audio['audio_obj']['title']}", ephemeral=True)
            else:
                bot.audio_controller.current_audio['loop'] = False
                if not button:
                    await interaction.response.send_message(f"Ended loop of {bot.audio_controller.current_audio['audio_obj']['title']}", ephemeral=True)
        except KeyError:
            pass

        ## Update queue embed
        if check_if_history(interaction.message):
            queue_embed = await build_queue_embed(interaction, bot, display_history=True)
        else:
            queue_embed = await build_queue_embed(interaction, bot)

        await interaction.edit_original_response(embed=queue_embed, view=AudioControls.generate_view(bot))
                    
    async def raise_volume(self, interaction: discord.Interaction, bot):

        try:
            if bot.audio_controller.muted is True:
                await self.mute_volume(interaction, bot)    
            voice_client = get(bot.voice_clients, guild=interaction.guild)
            ## raise volume 10%
            if voice_client:
                if bot.audio_controller.voice.source.volume >= 1.0:
                    return await interaction.followup.send(f"{interaction.user.mention} volume at max", ephemeral=True)
                bot.audio_controller.voice.source.volume = bot.audio_controller.voice.source.volume + 0.1
        except:
            pass
        ## Update queue embed
        if check_if_history(interaction.message):
            queue_embed = await build_queue_embed(interaction, bot, display_history=True)
        else:
            queue_embed = await build_queue_embed(interaction, bot)

        await interaction.edit_original_response(embed=queue_embed, view=AudioControls.generate_view(bot))

    

    async def lower_volume(self, interaction: discord.Interaction, bot):    
        try:
            if bot.audio_controller.muted is True:
                await self.mute_volume(interaction, bot)    
            voice_client = get(bot.voice_clients, guild=interaction.guild)
            ## raise volume 10%
            if voice_client:
                if bot.audio_controller.voice.source.volume <= 0:
                    return await interaction.followup.send(f"{interaction.user.mention} volume at minimum", ephemeral=True)                
                bot.audio_controller.voice.source.volume = bot.audio_controller.voice.source.volume - 0.1
        except:
            pass
        ## update queue embed
        if check_if_history(interaction.message):
            queue_embed = await build_queue_embed(interaction, bot, display_history=True)
        else:
            queue_embed = await build_queue_embed(interaction, bot)

        await interaction.edit_original_response(embed=queue_embed, view=AudioControls.generate_view(bot))
        
    async def stop_playback(self, interaction: discord.Interaction, bot, button=False):
        music_db = MusicHistory(bot.redis)
        ## Get the author's voice channel and make sure they are in a voice channel
        try:
            voice_channel = interaction.user.voice.channel
        except:
            if not button:
                return await interaction.response.send_message(f"{interaction.user.mention}, you need to be in a voice channel to stop tracks.", ephemeral=True)

        ## delete queue from database in case in didn't get deleted
        await music_db.delete_queue()


        ## Check to see if bot is currently playing something back
        if bot.audio_controller.voice is None and bot.audio_controller.transcription_sess is False:
            if interaction.is_expired():
                await interaction.followup.send(f"{interaction.user.mention}, I'm not currently playing anything.", ephemeral=True)
            else:
                try:
                    return await interaction.response.send_message(f"{interaction.user.mention}, I'm not currently playing anything.", ephemeral=True)
                except:
                    return await interaction.edit_original_response(content=f"{interaction.user.mention}, I'm not currently playing anything.")  
        ## store volume 
        try:
            volume = bot.audio_controller.voice.source.volume
            await music_db.store_volume(volume)
        except:
            print("Couldn't store volume!")
        

        #bot.audio_controller.queue_list = []
        if not button:
            await interaction.response.send_message('Stopping...', ephemeral=True)
        ## If the queue is empty just cut playback, otherwise add skip attribute
        try:
            bot.audio_controller.stop = True
            bot.audio_controller.transcription_sess = False
            bot.audio_controller.current_audio = None
            bot.audio_controller.voice = None
            bot.audio_controller.current_voice_channel = None
            bot.audio_controller.timer_coroutine.cancel()
        except:
            if not button:
                await interaction.edit_original_response(content=f"{interaction.user.mention} was not able to set bot audio attributes.")
                    

        try:
            voice_client = get(bot.voice_clients, guild=interaction.guild)
            await voice_client.disconnect()
        except:
            if not button:
                await interaction.edit_original_response(content=f"{interaction.user.mention} playback already stopped and bot has left voice.")
        
        ## Update queue embed
        # if check_if_history(interaction.message):
        #     queue_embed = await build_queue_embed(interaction, bot, display_history=True)
        # else:
        #     queue_embed = await build_queue_embed(interaction, bot)
        # await interaction.edit_original_response(embed=queue_embed, view=None)
        await interaction.edit_original_response(content=f"Playback stopped")

    async def resume_playback(self, interaction: discord.Interaction, bot, button=False):
        music_db = MusicHistory(bot.redis)
        queue_list = await music_db.retrieve_queue()
        ## Get the author's voice channel and make sure they are in a voice channel
        try:
            voice_channel = interaction.user.voice.channel
        except:
            if not button:
                return await interaction.response.send_message(f"{interaction.user.mention}, you need to be in a voice channel to resume tracks.", ephemeral=True)
        
        ## Check to see if bot is currently playing something back
        if bot.audio_controller.voice is None:
            if len(queue_list) > 0:
                return bot.loop.create_task(bot.audio_controller.play_audio())            
            else:
                return await interaction.response.send_message(f"{interaction.user.mention}, I'm not currently playing anything.", ephemeral=True)
        await interaction.response.send_message('Resuming...', ephemeral=True)
        ## If the queue is empty just cut playback, otherwise add skip attribute
        try:
            voice_client = get(bot.voice_clients, guild=interaction.guild)
            ## Make sure bot is actually paused
            if not voice_client.is_paused():
                if not button:
                    return await interaction.response.send_message(content=f"{interaction.user.mention}, I'm not currently paused.", ephemeral=True)
            else:
                voice_client.resume()
        except:
            if not button:
                await interaction.edit_original_response(content=f"{interaction.user.mention} failed to resume audio.")


    async def pause_playback(self, interaction: discord.Interaction, bot, button=False):
        ## Get the author's voice channel and make sure they are in a voice channel
        try:
            voice_channel = interaction.user.voice.channel
        except:
            if not button:
                return await interaction.response.send_message(f"{interaction.user.mention}, you need to be in a voice channel to pause tracks.", ephemeral=True)
        
        ## Check to see if bot is currently playing something back
        if bot.audio_controller.voice is None:
            if not button:
                return await interaction.response.send_message(f"{interaction.user.mention}, I'm not currently playing anything.", ephemeral=True)

        
        ## If the queue is empty just cut playback, otherwise add skip attribute
        try:
            voice_client = get(bot.voice_clients, guild=interaction.guild)
            if voice_client.is_paused():
                voice_client.resume()
                if not button:
                    await interaction.response.send_message('Resuming...', ephemeral=True)
            else:
                voice_client.pause()
                if not button:
                    await interaction.response.send_message('Pausing...', ephemeral=True)
        except:
            if not button:
                await interaction.edit_original_response(content=f"{interaction.user.mention} failed to pause audio.")

        ## Update queue embed
        if check_if_history(interaction.message):
            queue_embed = await build_queue_embed(interaction, bot, display_history=True)
        else:
            queue_embed = await build_queue_embed(interaction, bot)

        
        await interaction.edit_original_response(embed=queue_embed, view=AudioControls.generate_view(bot))
        

    async def skip_track(self, interaction: discord.Interaction, bot, button=False):
        music_db = MusicHistory(bot.redis)
        queue_list = await music_db.retrieve_queue()

        ## Get the author's voice channel and make sure they are in a voice channel
        try:
            voice_channel = interaction.user.voice.channel
        except:
            if not button:
                return await interaction.response.send_message(f"{interaction.user.mention}, you need to be in a voice channel to skip tracks.", ephemeral=True)
        
        ## Check to see if bot is currently playing something back
        if bot.audio_controller.voice is None:
            if not button:
                return await interaction.response.send_message(f"{interaction.user.mention}, I'm not currently playing anything.", ephemeral=True)

        bot.audio_controller.current_audio['loop'] = False

        if not button:
            await interaction.response.send_message('Skipping...', ephemeral=True)
        ## If the queue is empty just cut playback, otherwise add skip attribute
        if len(queue_list) <= 0:
            voice_client = get(bot.voice_clients, guild=interaction.guild)
            return await voice_client.disconnect()
        else:
            bot.audio_controller.skip_next = True

        #if bot.audio_controller.queue_list[0]['audio_obj']['title'] == bot.audio_controller.current_audio['audio_obj']['title']:
        #    bot.audio_controller.queue_list.pop(0)

        async def wait_for_next_track(bot, interaction):
            ## wait for a few seconds to make sure track has time to stop in the controller
            await asyncio.sleep(5)
            while True: 
                if bot.audio_controller.voice:
                    if not bot.audio_controller.voice.is_playing():
                        await asyncio.sleep(1)
                    else:
                        break
                else:
                    break

            queue_embed = await build_queue_embed(interaction, bot)
            control_view = AudioControls.generate_view(bot)
            await interaction.edit_original_response(embed=queue_embed, view=control_view)

        next_track_task = asyncio.create_task(wait_for_next_track(bot, interaction))
        await asyncio.wait_for(next_track_task, timeout=30)


async def build_queue_embed(interaction: discord.Interaction, bot, title="**Current song link**" ,display_history=False, stopped=False):
    music_db = MusicHistory(bot.redis)
    queue_list = await music_db.retrieve_queue()
    
    ## Check to see if bot is currently playing something back
    if bot.audio_controller.voice is not None and bot.audio_controller.current_audio is not None:
        #return await ctx.send(embed= discord.Embed(title="Blank Embed",description="none"))
        #return await interaction.response.send_message(f"{interaction.user.mention}, I'm not currently playing anything.", ephemeral=True)


        ## If the queue is empty just cut playback, otherwise add skip attribute
        try:
            voice_client = get(bot.voice_clients, guild=interaction.guild)
        except:
            pass

        playback_info = {
            'current_item':bot.audio_controller.current_audio,
            'queue_list':queue_list,
            
        }
        

        if hasattr(voice_client, 'channel'):
            playback_info['current_channel'] = voice_client.channel.name
        else:
            playback_info['current_channel'] = 'none'
        

        queue_embed = discord.Embed(title=title, url=bot.audio_controller.current_audio['audio_obj']['webpage_url'])
        if bot.audio_controller.current_audio['tts'] is True:
            queue_embed.add_field(name="Currently Transcribing using TTS Engine*",value=f"TTS Engine", inline=False)
        else:
            queue_embed.add_field(name="Title",value=f"{bot.audio_controller.current_audio['audio_obj']['title']}", inline=False)
            queue_embed.add_field(name="Progress", value=f"{round((bot.audio_controller.counter / bot.audio_controller.current_audio['audio_obj']['duration'])*100)}% ({convert_to_minutes(bot.audio_controller.counter)}/{convert_to_minutes(bot.audio_controller.current_audio['audio_obj']['duration'])})" )
            
            ## Volume logic
            if bot.audio_controller.voice.source:
                if bot.audio_controller.voice.source.volume is not None:
                    if bot.audio_controller.voice.source.volume >= 1.0:
                        bot.audio_controller.voice.source.volume = 1.0
                    if bot.audio_controller.voice.source.volume <= 0:
                        bot.audio_controller.voice.source.volume = 0
                    queue_embed.add_field(name='Volume', value=f"{round(bot.audio_controller.voice.source.volume*100)}%")
                
                
            if voice_client:
                if stopped is True:
                    status='*ended*'
                elif not voice_client.is_paused():
                    status = '*playing*'
                else:
                    status = '*paused*'

                if bot.audio_controller.current_audio['loop'] is True:
                    status += ' *(looping)*'

                queue_embed.add_field(name='Status', value=status)


            queue_embed.set_thumbnail(url=bot.audio_controller.current_audio['audio_obj']['thumbnail'])


        queue_embed.add_field(name="Requestor:", value=f"{bot.audio_controller.current_audio['requestor_name']}")
        queue_embed.add_field(name="Voice Channel:", value=f"{playback_info['current_channel']}")

        queue_text=""
        if len(queue_list) > 0:
            for audio in queue_list:
                if audio['tts'] is True:
                    queue_text+=f"**Voice transcription** *for {audio['requestor_name']}*\n"
                else:
                    queue_text+=f"**{audio['audio_obj']['title']}** *requested by {audio['requestor_name']}*\n"
            queue_embed.add_field(name="__**QUEUE**__",value=queue_text, inline=False)

    else:
        bot.audio_controller.voice = None
        bot.audio_controller.current_voice_channel = None
        bot.audio_controller.current_audio = None
        queue_embed = discord.Embed(title="**Queue History**")
        display_history=True

    if display_history is True:
        music_db = MusicHistory(bot.redis)
        history_list = await music_db.get_history()
        history_list.reverse()
        
        if history_list is not None:
            queue_embed.add_field(name="__**Latest 10 Tracks**__",value="\u200b", inline=False)
            if len(history_list) > 0:
                x=1
                for audio in history_list:
                    history_text=""
                    history_text+=f"[{audio['audio_obj']['title']}]({audio['link']}) \n"
                    
                    queue_embed.add_field(name=f"{x}: *{audio['requestor_name']}*", value=history_text, inline=False)
                    x+=1
                    
                
            else:
                queue_embed.add_field(name="No history to show",value='-', inline=False)
        else: 
            history_list = []
    return queue_embed
