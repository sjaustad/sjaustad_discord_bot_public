from collections import UserList
import discord, traceback, asyncio
from discord import app_commands
from discord.ext import commands
from gtts import  gTTS

from utils.messages.user_input import UserInput

class Transcribe_cog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="transcribe", description="This command will generate a text-to-speech session for you.")
    async def transcribe(self, interaction: discord.Interaction):

        ## Get the author's voice channel
        try:
            voice_channel = interaction.user.voice.channel
        except:
            return await interaction.response.send_message(f"{interaction.user.mention}, you need to be in a voice channel for me to play audio.", ephemeral=True)
        ## test if there is a transcribe session
        if self.bot.audio_controller.transcription_sess is True:
            return await interaction.response.send_message(f"{interaction.user.mention}, there is currently an active transcription session, please try again later.",ephemeral=True)
        
        original_name = interaction.guild.me.display_name
        ## change the nickname to be person subscribed
        await interaction.guild.me.edit(nick=f"{interaction.user.name}'s Translator")

        user_info = interaction.guild.get_member(interaction.user.id)
        self.bot.audio_controller.transcription_sess = True


        ## create text channel for them
        ## Only they can see it
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True)
        }
        try:
            new_channel = await interaction.guild.create_text_channel(f"{interaction.user.name}-transcription", overwrites = overwrites)#, category = voice_category)
        except:
            return await interaction.response.send_message(f"{interaction.user.mention} Failed to create text channel for transcription.")

        await interaction.response.send_message(f"Start using text-to-speech in this new channel I created for you: {new_channel.mention}.", ephemeral=True)

        ## start transcribe session
        await new_channel.send(f"{interaction.user.mention} Begin typing text now. 10 minutes of inactivity will end transcription. Type 'stop' to end.")
        voice = await voice_channel.connect()
        transcribe_session = self.bot.loop.create_task(self.transcribeSess(interaction, new_channel, voice, original_name))

        self.bot.loop.create_task(self.checkAudioChannel(interaction, voice, transcribe_session, original_name))
        


    async def transcribeSess(self, interaction, channel, voice, original_name):
        input = UserInput(self.bot)
        transcribe = True
        first = True
        try:
            while transcribe:
                user_response = await input.get_text_response(discord.Embed(title="none"), user=interaction.user, channel=channel, timeout=600, hide_display=True, delete_response=False)
                try:
                    if user_response['user_text'] is False or user_response['user_text'].lower() == 'stop': transcribe = False
                    else:
                        await self.play_audio(interaction, user_response['user_text'], voice, first)
                        first = False
                except:
                    await channel.send(f"{interaction.user.mention} I couldn't transcribe that last thing you sent, try something else.")
        except:
            pass
        self.bot.audio_controller.transcription_sess = False
        await voice.disconnect()
        await interaction.guild.me.edit(nick=original_name)
        await channel.delete()

    
    async def checkAudioChannel(self, interaction, voice, transcribe_session, original_name):
        while True:
            current_voice_state = interaction.guild.get_member(interaction.user.id)
            if current_voice_state.voice is None:
                try:
                    transcribe_session.cancel() 
                    await interaction.guild.me.edit(nick=original_name)
                    return await voice.disconnect()
                except: return
            if current_voice_state.voice.channel.id != voice.channel.id:
                try:
                    transcribe_session.cancel() 
                    await interaction.guild.me.edit(nick=original_name)
                    return await voice.disconnect()
                except: return
            if self.bot.audio_controller.transcription_sess is False:
                try: transcribe_session.cancel() 
                except: pass
                await interaction.guild.me.edit(nick=original_name)
                return
            
            await asyncio.sleep(3)
        

    async def play_audio(self, interaction, speech_text, voice, first=True):
        item = {
            'speech_text':speech_text,
            'language':"en",
            'tld':"com",
            'link':'speech_tts.mp3'
        }
        if first is True:
            item['speech_text'] = f"Now transcribing for {interaction.user.name}. " + speech_text

        tts_obj = gTTS(text=item['speech_text'], lang=item['language'], slow=False, tld=item['tld'])
        tts_obj.save(item['link'])

        voice.play(discord.FFmpegPCMAudio(item['link']))

    
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Transcribe_cog(bot))