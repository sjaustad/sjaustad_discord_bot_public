
import queue, pickle


endpoint = "server.ai_image"
class Queue:
    def __init__(self, redis):
        self.connector = redis

    def _format(self, attribute):
       return f"{endpoint}.{attribute}" 
    def _parent(self):
        return f"{endpoint}"
    
    async def add_to_queue(self, item):
        pickled_data = pickle.dumps(item)
        await self.connector.store(self._format(f"queue.{item['id']}"), pickled_data, raw=True)  
          

    async def get_queue(self):
        unpickled_data = []
        data = await self.connector.index_search(self._format("queue"), raw=True)
        for item in data:
            try:
                unpickled_data.append(pickle.loads(item['value']))
            except:
                pass
        #data = await self.connector.get()
        return unpickled_data

    async def retrieve_request(self, request_id):
        data = await self.connector.get(self._format(f"queue.{request_id}"),raw=True)
        if data is None: return data
        return pickle.loads(data)

    async def delete_request(self, request_id):
        return await self.connector.delete(self._format(f"queue.{request_id}"))
    
    async def get_image(self, request_id, user_id):
        data = await self.connector.get(self._format(f"completed.requests.{request_id}"),raw=True)
        return data

    async def delete_queue(self):
        current_queue = await self.get_queue()
        keys = []
        for item in current_queue:
            keys.append(item['key'])
        await self.connector.bulk_delete(keys)
    
    async def get_generator_server_ping(self):
        data = await self.connector.get(self._format(f"latest_ping"))
        return data

    async def get_completed_job(self, job_id):
        data = await self.connector.get(self._format(f"completed.requests.{job_id}"), raw=True)

        if data is not None:
            data = pickle.loads(data)
        return data
    
    async def delete_user_history(self, user_id):
        all_requests = await self.get_user_requests(user_id)

        keys = []
        for request in all_requests:
            keys.append(self._format(f"completed.{user_id}.{request['id']}"))
            keys.append(self._format(f"completed.requests.{request['id']}"))

        await self.connector.bulk_delete(keys)
    
    async def delete_completed_request(self, request_id):
        result = await self.connector.delete(self._format(f"completed.requests.{request_id}"))
        return result
    
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

    async def delete_all_requests(self):
        all_requests = await self.connector.complex_search(f"{endpoint}.completed*", skip_value = True)
        keys = []
        for request in all_requests:
            keys.append(request['key'])
        await self.connector.bulk_delete(keys)

    
    async def get_user_requests(self, user_id):
        requests = await self.connector.index_search(self._format(f"completed.{user_id}"), raw=True)
        if requests is None: return None
        unpickled_data = []
        for request in requests:
            unpickled_request = pickle.loads(request['value'])

            if not 'id' in unpickled_request:
                await self.connector.delete(request['key'])
            if not 'prompt' in unpickled_request:
                await self.connector.delete(request['key'])
            if not 'source_image_names' in unpickled_request:
                await self.connector.delete(request['key'])
            if not 'type' in unpickled_request:
                await self.connector.delete(request['key'])
            if not 'time' in unpickled_request:
                await self.connector.delete(request['key'])
            if 'grid_image' in unpickled_request:
                await self.connector.delete(request['key'])
            if 'source_images' in unpickled_request:
                await self.connector.delete(request['key'])

            unpickled_data.append(unpickled_request)

        return unpickled_data