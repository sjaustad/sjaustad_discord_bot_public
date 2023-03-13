from tabnanny import check
import discord, traceback
from discord import app_commands
from discord.ext import commands

class Help_cog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.ignore_list = ['sudo','unsudo','reload']

    @app_commands.command(name="help", description="Lists available commands")
    async def help(self, interaction: discord.Interaction):
        app_commands = self.bot.tree.get_commands()
        app_commands = sorted(app_commands, key=lambda x: x.name)
        help_embed = discord.Embed(title="Commands", description="All commands start with /. Presence of * indicates command has role restrictions.")

        for i in range(0, len(app_commands), 10):
            chunk = app_commands[i:i + 10]
            app_commands_text = ""

            for command in chunk:
                if command.name in self.ignore_list: continue
                ## check if it has sub commands
                sub_commands = False
                sub_commands_text = ""
                restricted = False
                if hasattr(command, 'commands'):

                    sub_commands = True
                    for sub_command in command.commands:
                        if sub_command.name in self.ignore_list: continue
                        if hasattr(sub_command,'checks'):
                            if len(sub_command.checks) >0:
                                restricted = True
                        sub_commands_text += f"{sub_command.name} - *{sub_command.description}*\n"


                if hasattr(command,'checks'):
                    if len(command.checks) >0:
                        restricted = True
    

                if command.description == '…':
                    description = ""
                else: description = f"*{command.description}*"
                if restricted is True:
                    app_commands_text += f"**{command.name}** *\n {description}"
                else:
                    app_commands_text += f"**{command.name}**\n {description}" 
                
                if sub_commands is True:
                    app_commands_text += sub_commands_text
                
                app_commands_text += "\n\n"

            help_embed.add_field(name="\u200b", value=app_commands_text)
        await interaction.response.send_message(embed=help_embed, ephemeral=True)
    
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Help_cog(bot))