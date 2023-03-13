import discord
endpoint = "server.polls"
class Polls:
    def __init__(self, redis):
        self.connector = redis
        
    def _format(self, attribute):
       return f"{endpoint}.{attribute}" 
    def _parent(self):
        return f"{endpoint}"

    ## store user results as they come in
    async def store_poll_entry(self, poll_id: int, user, option):
        user_data ={
            'id':user.id,
            'option':option
        }
        poll = await self.get_poll_results(poll_id)

        poll['results'].append(user_data)
        return await self.connector.store(self._format(poll_id), poll)

    ## update entire poll (used when someone is removed)
    async def update_poll(self, poll:dict):
        return await self.connector.store(self._format(poll['poll_id']), poll)

    ## get database entry for the poll
    async def get_poll_results(self, poll_id: int):
        data = await self.connector.get(self._format(poll_id))
        return data

    ## message_id will be called poll_id also
    async def initial_poll_store(self, message_id: int, creator: discord.User, options: list):
        poll_data = {
            'creator':creator.id,
            'poll_id':message_id,
            'options':options,
            'results':[]
        }
        return await self.connector.store(self._format(message_id), poll_data)
