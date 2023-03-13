import requests, os, csv, asyncio, json

from dateutil.parser import parse
from datetime import datetime
from IGDB_API import API as IGDB_API
from GamepassDBFunctions import GamepassDBFunctions


igdb_api = IGDB_API()
max_day_allowance = 35
csv_url = "https://docs.google.com/spreadsheets/d/1kspw-4paT-eE5-mrCrc4R9tg70lH2ZTFrJOUmOtOytg/export?format=csv"
res = requests.get(url=csv_url)


from utils.database import connector_async
redis_async = connector_async.Async_Redis()

loop=asyncio.get_event_loop()
loop.run_until_complete(redis_async.create_pool())

gamepass_db = GamepassDBFunctions(redis_async)
    

async def updateGamepassInfo():


    ## Download CSV file
    game_list_csv_name = 'test.csv'
    open(game_list_csv_name, 'wb').write(res.content)

    ## Open CSV file and convert to list of dictionaries
    f=open(game_list_csv_name, "r")
    all_lines = f.readlines()

    # first line is garbage, so get rid of it
    all_lines = all_lines[1:]
    reader = csv.DictReader(all_lines)
    game_list = list(reader)

    ## delete all games
    await gamepass_db.delete_all_games()


    metacritic_filter = None
    valid_games = []
    ## Filter list for variables
    for game in game_list:
        
        ## Make sure it's PC
        if game['System'] != 'PC' and game['System'] != 'Xbox / PC':
            continue

        ## Make sure it's active
        if game['Status'] == "Active" or game['Status'] == 'Leaving Soon':
            pass
        else: continue

        ## Meta critic filter
        if metacritic_filter is not None:
            try:
                metacritic_score = int(game['Metacritic'])
            except:
                continue # could not parse it
            if metacritic_score < metacritic_filter:
                continue

        ## TESTING REMOVE ME ##
        #if game['Game'] != "SimCity 4: Deluxe Edition": continue

        valid_games.append(game)




    ## Get gamemodes
    end_point = "game_modes"
    game_mode_data = """
    fields checksum,created_at,name,slug,updated_at,url;
    """

    game_modes = await igdb_api.apiRequest(end_point, game_mode_data)

    end_point = "games"

    processed_game_list = []

    for game in valid_games:
        data = """
        fields name, platforms, first_release_date, game_modes, cover; 
        where release_dates.platform = (6);
        """ # consider adding multiplayer_modes in future
        possible_games = []
        data += f"search \"{game['Game']}\";"
        matched_games = await igdb_api.apiRequest(end_point, data)
        game['game_modes'] = []
        game['Release'] = parse(game['Release'])
        game['Added'] = parse(game['Added'])
        if game['xCloud'].lower() == 'yes':
            game['xCloud'] = 1
        else: game['xCloud'] = 0

        if game['Metacritic'] is None or game['Metacritic'] == '':
            game['Metacritic'] = 0
        else: game['Metacritic'] = float(game['Metacritic'])

        if game['Age'] is None or game['Age'] == '':
            game['Age'] = 0
        else: game['Age'] = float(game['Age'])

        if len(matched_games) > 1:
            for matched_game in matched_games:
                try:
                    matched_game['release_date'] = datetime.utcfromtimestamp(matched_game['first_release_date'])
                except KeyError:
                    print(f"Failed to process {game['Game']}: no release date")
                    continue

                diff_days = abs((game['Release'] - matched_game['release_date']).days)
                if diff_days < max_day_allowance:
                    matched_game['diff_days'] = diff_days
                    possible_games.append(matched_game)
            if len(possible_games) <= 0:
                print(f"Failed to process {game['Game']}: no acceptable matches found")
            else:
                closest_date_game = min(possible_games, key=lambda x:x['diff_days'])
            
        elif len(matched_games) == 1:
            closest_date_game = matched_games[0]
        else:
            print(f"Failed to process {game['Game']}: no matches from IGDB found")

        try:
            for game_mode in closest_date_game['game_modes']:
                game['game_modes'].append(game_modes[game_mode - 1]['slug'])
        except KeyError:
            print(f"Failed to process {game['Game']}: no game modes")

        ## Get cover art:
        try:
            cover_end_point = "covers"
            cover_data = f"fields url; where id = {closest_date_game['cover']};"
            cover_url = (await igdb_api.apiRequest(cover_end_point, cover_data))[0]['url'].rsplit('/', 1)[-1]
            cover_url = "https://images.igdb.com/igdb/image/upload/t_cover_big/" + cover_url
            game['cover_url'] = cover_url
        except:
            game['cover_url'] = None
            pass # Whatever...

        #game['game_modes'] = ",".join(game['game_modes'])
        processed_game_list.append(game)

        #addToDatabase(game)
        print(f"Processed {game['Game']}")
        
    await gamepass_db.store_all_games(processed_game_list)




loop.run_until_complete(updateGamepassInfo())
"""
## Write back to CSV
keys = valid_games[0].keys()
with open('gamepass_list.csv', 'w', newline='')  as output_file:
    dict_writer = csv.DictWriter(output_file, keys)
    dict_writer.writeheader()
    dict_writer.writerows(valid_games)
"""