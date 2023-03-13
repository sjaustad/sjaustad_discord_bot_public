import discord, psutil, platform
from discord import app_commands
from discord.ext import commands

class Status_cog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="status", description="Displays current server status")

    async def status(self, interaction: discord.Interaction):

        embed = discord.Embed(title="Bot Status", description="Server Info", color=discord.Color.green())
        cpu_usage = psutil.cpu_percent()
        ram_usage = psutil.virtual_memory()
        ram_total = round(ram_usage.total / 1073741274, 2)
        ram_used = round(ram_usage.used / 1073741274,2)
        ram_avail = round(ram_usage.available / 1073741274,2)
        external_ip = externalIP()

        embed.add_field(name="Status:",value="Online 🟢")
        embed.add_field(name="CPU usage:", value=f"{cpu_usage}%")
        embed.add_field(name="RAM Usage:", value=f"{ram_used}/{ram_total}GB ({ram_usage.percent}%)")
        
        embed.add_field(name="IP:",value=external_ip)

        server = interaction.guild
        if server is not None:
            embed.add_field(name="Users on server:",value=server.member_count)
            #embed.add_field(name="Server Region:", value=server.region, inline=True)
        test = platform.system()
        embed.add_field(name="Running on:", value=f"{platform.system()}. Python {platform.python_version()} 🐍")

        # app_list = Apps.monitor.checkAllApps()
        # headers = ["[App Name]","[Status]","[Port]"]
        # table = []

        # for app in app_list:
        #     table.extend([[app['appName'],app['currentState'],app['port']]])

        await interaction.response.send_message(embed=embed, ephemeral=True)
        #await displayLongList(ctx, table, headers, source_embed=embed)
    
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Status_cog(bot))

def externalIP():
    import urllib.request
    external_ip = urllib.request.urlopen('https://ident.me').read().decode('utf8')
    return external_ip