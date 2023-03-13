from settings.server_settings import settings
settings = settings()

endpoint = "server.help"
class Help:
    def __init__(self, redis):
        self.connector = redis
    def _format(self, command_id):
       return f"{endpoint}.{command_id}" 
    def _parent(self):
        return f"{endpoint}"
    
    async def get_all_commands(self):
        data = await self.connector.index_search(endpoint)
        return data

    async def write_help_list_file(self):
        all_commands = await self.connector.index_search(endpoint)
        command_str = ""
        for command in all_commands:
            command_str += command['value']['command_id'] + "\n"
        help_list_path = settings.server.base_dir  + "/cogs/files/help_list.txt"
        with open(help_list_path, 'w') as f:
            f.write(command_str)

    async def get_help(self, command_id):
        data = await self.connector.get(self._format(command_id))
        return data
    
    async def add_help(self, command_id, command_dict):
        result = await self.connector.store(self._format(command_id), command_dict)
        

