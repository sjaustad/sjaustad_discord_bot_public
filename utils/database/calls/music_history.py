
from asyncio import QueueEmpty
import queue


endpoint = "server.music"
class MusicHistory:
    def __init__(self, redis):
        self.connector = redis
        
    def _format(self, attribute):
       return f"{endpoint}.{attribute}" 
    def _parent(self):
        return f"{endpoint}"
        
    async def add_to_ban_list(self, user_id):
        banned_users = await self.get_ban_list()
        if user_id in banned_users: return False

        banned_users.append(user_id)
        await self.connector.store(self._format(f"ban_list"), banned_users)

    async def remove_from_ban_list(self, user_id):
        banned_users = await self.get_ban_list()
        if not user_id in banned_users: return False
        banned_users.remove(user_id)
        await self.connector.store(self._format(f"ban_list"), banned_users)

    async def get_ban_list(self):
        banned_users = await self.connector.get(self._format(f"ban_list"))
        if banned_users is None: 
            banned_users = []
        return banned_users

    async def store_volume(self, volume: float):
        return await self.connector.store(self._format("volume"), volume)
    
    async def get_volume(self):
        data = await self.connector.get(self._format("volume"))
        try:
            data = float(data)
        except:
            data = 0.80
        return data

    async def get_history(self):
        data= await self.connector.get(self._format("history"))
        return data
    
    async def store_history(self, audio_info):
        
        audio_dict = audio_info.copy()
        data = await self.connector.get(self._format("history"))
        if data is not None:
            if len(data) >= 10:
                data.pop(0)
        else:
            data = []
        data.append(audio_dict)
        await self.connector.store(self._format("history"), data)

    async def clear_history(self):
        await self.connector.store(self._format("history"), [])


## QUEUE Functions
    async def add_to_queue(self, audio):
        current_queue = await self.retrieve_queue()
        if current_queue is None:
            current_queue = []
        current_queue.append(audio)
        return await self.connector.store(self._format("queue"), current_queue)


    async def delete_queue(self):
        return await self.connector.delete(self._format("queue"))


    async def retrieve_queue(self):
        queue_list=  await self.connector.get(self._format("queue"))
        if queue_list is None:
            queue_list = []
        return queue_list

    async def remove_first_from_queue(self):
        current_queue = await self.retrieve_queue()
        current_queue.pop(0)
        return await self.connector.store(self._format("queue"), current_queue)
