
endpoint = "reddit_posts"
class Reddit:
    def __init__(self, redis):
        self.connector = redis
    def _format(self, attribute):
       return f"{endpoint}.{attribute}" 
    def _parent(self):
        return f"{endpoint}"

    async def check_post(self, post_dict):
        data = await self.connector.get(self._format(post_dict['id']))
        if data is None:
            await self._add_post(post_dict)
    
    async def _add_post(self, post_dict):
        result = await self.connector.store(self._format(post_dict['id']), post_dict)
        return result
