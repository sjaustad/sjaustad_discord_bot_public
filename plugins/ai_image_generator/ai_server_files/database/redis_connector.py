
from database.redis_settings import settings
import orjson, aioredis

from concurrent.futures.thread import ThreadPoolExecutor
import asyncio


class Async_Redis:
    def __init__(self) -> None:
        self.max_retries =3


    async def create_pool(self):
        #self.redis = aioredis.from_url(f"redis://:{settings.database.password}@{settings.database.host}:6379/", db=settings.database.db)
        self.redis = await aioredis.from_url(f"redis://{settings.database.host}:6379", password=settings.database.password, db=settings.database.db)
        
    ##### SINGLE COMMANDS #####

    # def get_connection():
    #     global _connection
    #     if not _connection:
    #         print("Connecting to Redis database...")
    #         #_connection = redis.Redis(host=settings.database.host, port=settings.database.port, db=settings.database.db, password=settings.database.password)
    #         _connection = aioredis.from_url(f"redis://:{settings.database.password}@{settings.database.host}", db=settings.database.db)
    #     return _connection
    async def store(self, key, data, index=True, raw=False):
        if raw is False:
            json_data = orjson.dumps(data)
        else: 
            json_data = data
    
        attempts = 0
        while attempts < self.max_retries:
            try:
                result = await self.redis.set(key, json_data)
                break
            except ConnectionError:
                asyncio.sleep(3)
                attempts += 1
                if attempts == self.max_retries: return False
                
        ## index
        if index is True:
            parent_str = '.'.join(key.split('.')[:-1]) + ".index"
            await self.redis.sadd(parent_str, key)
        return result
    async def get(self, key, raw=False):
        json_data = await self.redis.get(key)
        if json_data is None: return None
        if raw is False:
            try:
                data = orjson.loads(json_data)
            except TypeError:
                return None
        else: data = json_data
        return data
    

    async def delete(self, key):
        result = await self.redis.delete(key)
        parent_str = '.'.join(key.split('.')[:-1]) + ".index"
        await self.redis.srem(parent_str, key)
        return result
    
    async def incr(self, key, amount=1):
        return await self.redis.incr(key, amount)
        
    async def decr(self, key, amount=1):
        return await self.redis.decr(key, amount)        


    ##### BULK COMMANDS #####

    ## accepts large sets of data from a list in the form of item['key'] and item['value']
    ## item['value'] can contain any datatype supported by orjson included nested dictionaries
    async def bulk_store(self, data_set, index=True):
        chunks = [data_set[x:x+100] for x in range(0, len(data_set), 100)]
        for chunk in chunks:
            pipeline = await self.redis.pipeline()
            for item in chunk:
                json_data = orjson.dumps(item['value'])
                pipeline.set(item['key'], json_data)

                if index is True:
                    parent_str = '.'.join(item['key'].split('.')[:-1]) + ".index"
                    pipeline.sadd(parent_str, item['key'])
            await pipeline.execute()
        
    ## accepts a list of string keys and programmatically deletes all of them in the list
    async def bulk_delete(self, key_list):
        chunks = [key_list[x:x+100] for x in range(0, len(key_list), 100)]
        for key_list in chunks:
            pipeline = await self.redis.pipeline()
            for key in key_list:
                pipeline.delete(key)
                parent_str = '.'.join(key.split('.')[:-1]) + ".index"
                pipeline.srem(parent_str, key)
            await pipeline.execute()

    ## accepts an index parent as string
    ## example: users exist at the key structure users.username
    ## to find all users, pass this function 'users' and it will search for
    ## all users using 'users.index' tag. Values must already have index for
    ## this to work. If you cannot do not have an index, use the complex search function
    async def index_search(self, parent, raw=False):
        json_data = await self.redis.smembers(f"{parent}.index")
        pipeline = await self.redis.pipeline()
        if json_data is not None:
            keys = []
            json_data = dict.fromkeys(json_data, 0)
            result_list = []
            for key in json_data.keys():
                decoded_key = key.decode()
                pipeline.get(decoded_key)
                result_list.append({
                    'key':decoded_key
                })
                
            pipeline_results = await pipeline.execute()

            for x in range(0,len(result_list)):
                if raw is False:
                    try:
                        data = orjson.loads(pipeline_results[x])
                    except Exception as e:
                        print(f"Error serializing in connector.py: \n {e}")
                        data = None
                else: data= pipeline_results[x]
                result_list[x]['value'] = data   
            return result_list
        else: return json_data
    ## accepts a key value search using asterisks for wild cards
    ## example: find all users with a voice channel: 'users.*.voice_channel'
    async def complex_search(self, key_string):
        results = []
        #keys = await self.redis.scan_iter(key_string)
        cur = b'0'
        while cur:
            cur, keys = await self.redis.scan(cur, match=key_string)

    
        for key in keys:
            decoded_key = key.decode()
            if not decoded_key.endswith('.index'):
                value = await self.get(decoded_key)
                result_dict = {
                    'key':decoded_key,
                    'value':value
                }
                results.append(result_dict)

        return results    



    # List of stuff accessible to importers of this module. Just in case
    __all__ = [ 'getConnection' ]
