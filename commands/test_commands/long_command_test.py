from code import interact
from threading import Thread
import discord, traceback
from discord import app_commands
from discord.ext import commands
from discord.ui import Select
import asyncio
import time
from concurrent.futures.thread import ThreadPoolExecutor

class LongCommand_cog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="long", description="test for long commands")
    async def long_command(self, interaction: discord.Interaction):
        await interaction.response.defer()
        loop = asyncio.get_running_loop()
        executor = ThreadPoolExecutor(max_workers=4)
        future = loop.run_in_executor(executor, blocking_task)
        results = await asyncio.gather(future)
        await interaction.edit_original_response(embed=discord.Embed(title="Finished after 5 seconds!"))
        #await interaction.followup.send(f"Finished waiting 10 seconds!", ephemeral=True)

def blocking_task():
    ## blocking
    time.sleep(5)
    

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(LongCommand_cog(bot))