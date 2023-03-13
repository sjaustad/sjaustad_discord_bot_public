from discord.ext import commands
import discord, aioredis, os

from settings.server_settings import settings

TEST_GUILD = discord.Object(id=settings.discord.test_guild)

## on command error: ?tag appcommanderror


# after using setup_hook
class MyBot(commands.Bot):
    def __init__(self, redis):
        intents = discord.Intents.all()
        super().__init__(intents=intents, command_prefix=settings.discord.commandprefix)
        #self.tree = discord.app_commands.CommandTree(self)
        self.test_guild = TEST_GUILD
        #self.command_prefix = settings.discord.commandprefix
        #self.case_insensitive = True
        self.remove_command('help')
        self.redis = redis
        self.settings = settings()
        pass


    async def on_ready(self):
        print(f'Bot started as {self.user}')
    
    async def setup_hook(self) -> None:
        #self.tree.clear_commands(guild=TEST_GUILD)
        #self.tree.clear_commands(guild=None)
        print("Started setup hooks")
        await self.load_extensions()
        self.tree.copy_global_to(guild=TEST_GUILD)
        await self.tree.sync(guild=TEST_GUILD)
        
        # Load plugins

        ## Start Google API integration
        from plugins.google_drive_uploader.DriveConnector import DriveConnector
        DriveAPI=DriveConnector()
        self.DriveAPI = DriveAPI

        print("Finished setup hooks!")
                


    async def load_extensions(self):
        await self.load_extension('commands.global_error_handler')

        extension_folders=['commands/public','commands/restricted']#,'commands/test_commands']

        for folder in extension_folders:

            #path = os.getcwd()
            #folder = path + "/commands/public_commands"
            command_list = []
            for entry in os.scandir(folder):
                if entry.is_file() and entry.name[-3:] == '.py':
                    command_list.append(os.path.splitext(entry.name)[0])

            for command in command_list:
                cog_name = folder.replace('/','.') + "."
                await self.load_extension(cog_name + command)