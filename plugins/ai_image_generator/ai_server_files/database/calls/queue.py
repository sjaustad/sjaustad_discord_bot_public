
from curses import raw
import queue, datetime, pickle


endpoint = "server.ai_image"
class Queue:
    def __init__(self, redis):
        self.connector = redis

    def _format(self, attribute):
       return f"{endpoint}.{attribute}" 
    def _parent(self):
        return f"{endpoint}"
    
    async def delete_queue(self):
        current_queue = await self.get_queue()
        keys = []
        for item in current_queue:
            keys.append(item['key'])
        await self.connector.bulk_delete(keys)


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


    async def update_status(self, request, status):
        request['status'] = status
        result = await self.connector.store(self._format(f"queue.{request['id']}"), pickle.dumps(request), raw=True)
        return result


    async def store_data_simple(self, request_id, post_processing_data):
        pickled_info = pickle.dumps(post_processing_data)
        result = await self.connector.store(self._format(f"completed.{post_processing_data['requestor']}.{request_id}"), pickled_info, raw=True)
        return result

    async def store_data_full(self, request_id, post_processing_data):
        pickled_info = pickle.dumps(post_processing_data)
        result = await self.connector.store(self._format(f"completed.requests.{request_id}"), pickled_info, raw=True)
        return result

    async def store_image(self, image, image_key):
        pickled_image = pickle.dumps(image)
        result = await self.connector.store(self._format(f"images.{image_key}"), pickled_image, raw=True)
        return result

    async def mark_finished(self, request):
        request['done'] = True
        result = await self.connector.store(self._format(f"queue.{request['id']}"), pickle.dumps(request), raw=True)
        return result
    
    async def publish_time(self):
        result = await self.connector.store(self._format(f"latest_ping"), datetime.datetime.now())
        return result

    async def get_completed_job(self, job_id):
        data = await self.connector.get(self._format(f"completed.requests.{job_id}"), raw=True)

        if data is not None:
            data = pickle.loads(data)
        return data
    async def delete_request(self, request_id):
        return await self.connector.delete(self._format(f"queue.{request_id}"))
