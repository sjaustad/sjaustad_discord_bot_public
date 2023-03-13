import discord, traceback, os, random
from discord import app_commands
from discord.ext import commands


from settings.server_settings import settings

class PatternCommands_cog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="p", description="See the pattern")
    async def p(self, interaction: discord.Interaction):
        ## get random image
        dir = 'plugins/pattern/image_guess/src/'
        all_files = os.listdir(dir)
        image_file = random.choice(all_files)
        attachments = [discord.File(dir+image_file)]
        await interaction.response.send_message(files=attachments, ephemeral=True)
    @app_commands.command(name="pattern_guess", description="Guess the pattern and win money!")
    async def pattern_guess(self, interaction: discord.Interaction, guess:str):
        guess = guess.lower()
        valid_matches = [
            "st peter's basilica",
            "st peters basilica",
            "st. peter's basilica",
            "st. peters basilica",
            "st peter basilica",
            "st. peter basilica",
            "the papal basilica of saint peter in the vatican",
            "papal basilica of saint peter in the vatican",
            "papal basilica of saint peter",
            "papal basilica of st. peter",
            "papal basilica of st peter",
            "basilica papale di san pietro",
            "basilica papale di san pietro in vaticano",
        ]
        if guess in valid_matches:
            ## Correct!
            await interaction.response.send_message(f"You are correct, the location is The Papal Basilica of Saint Peter in the Vatican! If you were first, you will receive the prize, the pattern master has already been notified.", ephemeral=True)


            ## send notification to admin
            test_channel = self.bot.get_channel(getattr(settings.guilds,str(interaction.guild.id)).server.channels.testchannel)
            patter_embed = discord.Embed(title="Someone solved the pattern!", description=f"{test_channel.mention}")
            patter_embed.add_field(name="Pattern Solver:",value=f"{interaction.user.mention}")
            await test_channel.send(embed=patter_embed)
            correct = True
        else:
            await interaction.response.send_message(f"It is not {guess}",ephemeral=True)
            correct = False
        dir = 'plugins/pattern/image_guess/'
        ## log guess
        with open(dir+"log.txt","a+") as file:
            file.write(f"{interaction.user.name},{guess},{correct}\n")

    
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PatternCommands_cog(bot))