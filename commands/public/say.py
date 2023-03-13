from code import interact
import discord, traceback
from discord import app_commands
from discord.ext import commands
from discord.ui import Select

class Say_cog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="say", description="Bot will say your text in a voice channel that you are in.")
    async def say(self, interaction: discord.Interaction, text_to_speech: str):
        #return await interaction.response.send_message(f"you said: {text_to_speech}",ephemeral=True)
        #return await interaction.response.send_message(f"{interaction.user.mention}, you didn't tell me anything to say!", ephemeral=True)
        
        if len(text_to_speech) == 0: return await interaction.response.send_message(f"{interaction.user.mention}, you didn't tell me anything to say!")

        if self.bot.audio_controller.transcription_sess is True:
            return await interaction.response.send_message(f"{interaction.user.mention}, there is currently an active transcription session, please try again later.", ephemeral=True)

        ## Get the author's voice channel
        try:
            voice_channel = interaction.user.voice.channel
        except:
            return await interaction.response.send_message(f"{interaction.user.mention}, you need to be in a voice channel for me to play audio.", ephemeral=True)
        
        await interaction.response.defer(ephemeral=True)

        user_name = interaction.user.name
        speech_text = f"Message from {user_name}. "  + text_to_speech
        language = "en"
        tld="com"

        ## Speak output file
        #voice = await voice_channel.connect()
        #voice.play(FFmpegPCMAudio("speech_tts.mp3"))
        stream= False
        
        status = await self.bot.audio_controller.add_to_queue(self.bot, voice_channel, interaction.user, stream, speech_text=speech_text, tts=True, language=language, tld=tld)
        if status is False: await interaction.followup.send(f"{interaction.user.mention}, your audio has been added to the queue.")
        else:
            await interaction.followup.send(f"{interaction.user.mention} loading TTS...")
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Say_cog(bot))