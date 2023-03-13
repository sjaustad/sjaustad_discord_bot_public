import sys, os, re
sys.path.append(os.path.abspath('.'))

regex = re.compile('[^A-Za-z0-9]+')

endpoint = "server.gamepass"
class GamepassDBFunctions:
    def __init__(self, redis):
        self.connector = redis

    def _format(self, attribute):
       return f"{endpoint}.{attribute}" 
    def _parent(self):
        return f"{endpoint}"

    async def store_all_games(self, game_list):
        db_data = []
        for game in game_list:
            db_data.append({
                'key':self._format(regex.sub('', game['Game'].lower())),
                'value':game
            })
        await self.connector.bulk_store(db_data)

    ## Get all games
    async def retrieve_all_games(self, game_filter=None):
        data = await self.connector.index_search(endpoint)
        return data

    ## Get one game
    async def retrieve_game(self, game_title):
        game_info = await self.connector.get(self._format(game_title))
        return game_info

    async def retrieve_like_game(self, game_title):
        games = await self.connector.complex_search(f"{endpoint}.*{game_title.lower()}*")
        return games

    ## Add new game or update
    async def update_game_info(self, game_info):
        ## regex to make sure we don't get weird values stored as keys
        await self.connector.store(self._format(regex.sub('', game_info['Game'].lower())), game_info)

    ## Do not use, only have it here because a lot of keys needed to be deleted that weren't index and the names chagnes
    async def slow_search(self):
        games = await self.connector.complex_search(f"{endpoint}.*")
        for game_info in games:
            game_info['value']['game_modes'] = game_info['value']['game_modes'].split(",")
        return games

    ## Delete all gamepass games in refresh
    async def delete_all_games(self):
        #all_games = self.retrieve_all_games()
        all_games = await self.retrieve_all_games()
        key_list = []
        for game in all_games:
            key_list.append(game['key'])
            #connector.delete(game['key'])
        await self.connector.bulk_delete(key_list)
        return