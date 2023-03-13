

endpoint = "server"
class Server:
    def __init__(self, redis):
        self.connector = redis

    def _format(self, attribute):
       return f"{endpoint}.{attribute}" 
    def _parent(self):
        return f"{endpoint}"

    async def get_attribute(self, attribute):
        data = await self.connector.get(self._format(attribute))
        return data
    async def set_attribute(self, attribute, value, index=True):
        if index is True:
            result = await self.connector.store(self._format(attribute), value)
        else:
            result = await self.connector.store(self._format(attribute), value)
        return result
    async def remove_attribute(self, attribute):
        result = await self.connector.delete(self._format(attribute))
    async def index_search(self, attribute):
        index = self._format(attribute)
        data = await self.connector.index_search(index)
        return data
    ## adds to count
    async def increment(self, attribute, amount=1):
        return await self.connector.incr(self._format(attribute), amount=amount)
    ## decreases count
    async def decrement(self, attribute, amount=1):
        return await self.connector.decr(self._format(attribute), amount=amount)

    # async def add_sub_channel(self, guild_id, channel_info):
    #     await self.connector.store(f"{endpoint}.{guild_id}.sub_channel", channel_info)
    
    # async def remove_sub_channel(self, guild_id)
    #     await self.connector.store(f"{endpoint}.{guild_id}.sub_channel")