
endpoint = "users"
class Users:
    def __init__(self, redis):
        self.connector = redis

    def _format(self, id, attribute):
       return f"{endpoint}.{id}.{attribute}" 
    def _parent(self,id):
        return f"{endpoint}.{id}"


    ## SINGLES
    async def get_attribute(self, user_id, attribute):
        data = await self.connector.get(self._format(user_id, attribute))
        return data
    async def set_attribute(self, user_id, attribute, value):
        result =await self.connector.store(self._format(user_id, attribute), value)
        return result
    async def remove_attribute(self, user_id, attribute):
        result = await self.connector.delete(self._format(user_id, attribute))
        return result
    async def get_attributes_single_user(self, user_id):
        data = await self.connector.index_search(self._parent(user_id))
        return data


    ## MULTIS
    async def get_one_attribute_all_users(self, attribute):
        data = await self.connector.complex_search(f"{endpoint}.*.{attribute}")
        return data
    async def get_all_users_attributes(self):
        data = await self.connector.complex_search(f"{endpoint}.*")
        return data