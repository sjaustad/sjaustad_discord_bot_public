import discord
from discord.ext import commands

## Create a class for the command with any name to define the class
class CommandName(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    ## Specify the actual name of the command people type in discord with 
    ## 'name'. Also specify alias in the list.
    @commands.command(name="command",aliases=['execute','run','do'])
    ## Specify a role for the command to allow people to use it. This is 
    ## optional and if you don't include a role anyone can use the command
    ## including in private messages.
    @commands.has_role('Role')
    async def commandFunction(self, ctx, *args):
        ## Define Function here
        pass

## Required for discord to import the extension. Name must match above class name
async def setup(bot):
    await bot.add_cog(CommandName(bot))

## Define helper functions anywhere outside of the class
def helperFunction(ctx):
    pass