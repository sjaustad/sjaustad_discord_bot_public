#from discord_slash.utils.manage_commands import create_permission
#from discord_slash.model import SlashCommandPermissionType
import importlib
with open('./settings/base_dir.txt','r') as file:
    base_dir = file.readline().rstrip()

class settings:
    def __init__(self):
        guild_ids=[1234567890,1234567891] ## server ID list
        guilds = []
        for guild in guild_ids:
            guild_module = importlib.import_module(f'settings.servers.{guild}')
            guilds.append(guild_module)
            setattr(self.guilds, str(guild), guild_module)
            
    class database:
        ## Redis Database info
        host = '127.0.0.1'
        port = 6379
        db=0
        password='{{password}}'

    class discord:
        guild_ids=[1234567890,1234567891] ## server ID list
        guilds = []
        for guild in guild_ids:
            guild_module = importlib.import_module(f'settings.servers.{guild}')
            guilds.append(guild_module)
            
        apitoken='{{api key}}'
        clientid='{{client_id}}' ## OAuth Client ID - I don't think this is needed
        guildid={{guild_id}} ## Main server ID
        test_guild={{guild_id_test}}
        commandprefix='/'
        botadmin ='{{admin_name}}'

    class guilds:
        pass

    class googledrive:
        credentiallocation=f'{base_dir}/plugins/google_drive_uploader/credentials.json'
        scope='https://www.googleapis.com/auth/drive' ## READ ONLY--> 'https://www.googleapis.com/auth/drive.readonly.metadata'
        uploadfolderid='{{folder_id}}'
    class server:
        timezone="MST/MDT"
        key="{{key}}"
        token_timeout=2 #hours
        base_dir = base_dir
    class botconfig:
        ConfigurationDirectory=f'{base_dir}/settings/bot_config'
        PluginDirectory=f'{base_dir}/discord_commands'
        LogDirectory=f'{base_dir}/logs/bot_logs'
    class logs:
        log_subdir="/logs/commands/"
        function_log_subdir="/logs/functions/"
        bug_subdir="/logs/bug_reports/"
        db_log="/logs/db_log.txt"
        command_log="/logs/command_log.txt"
        error_log = "/logs/error_log.txt"
