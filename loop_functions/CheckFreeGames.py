import os, discord, asyncio, requests, json, re
from datetime import datetime
from settings.server_settings import settings
settings = settings()
from logs.logger import errorLogger, functionLogger

## import database functions
from utils.database.calls.reddit_posts import Reddit
posts = Reddit()

thisFunction = "checkFreeGames"
async def checkFreeGames(bot):
    url = "https://www.reddit.com/r/FreeGameFindings/hot/.json?limit=10"
    try:
        reddit_info_raw = requests.get(url, headers = {'User-agent': 'your bot 0.1'})
    except: errorLogger(thisFunction, f"Couldn't reach Reddit!")
    reddit_info = json.loads(reddit_info_raw.text)

    formatted_posts = []

    for post in reddit_info['data']['children']:
        post_title = post['data']['title']
        if post['data']['stickied'] == True:
            continue
        try:
            platform = re.findall(r'\[(.+)\]', post_title)[0]
        except:
            platform = "Not available"
        try:
            post_type = re.findall(r'\((.+)\)', post_title)[0]
        except:
            post_type = "Not available"
        try:
            title = post_title.split(")",1)[1]
        except:
            try:
                title = post_title.split("]",1)[1]
            except:
                title = post_title
        post_time = datetime.fromtimestamp(post['data']['created_utc'])

        if post_type.lower() == "game" or post_type == "Not available":
            post_data = {
                "title":title,
                "platform":platform,
                "url":post['data']['url'],
                "id":post['data']['id'],
                "posturl":post['data']['permalink'],
                "thumbnail":post['data']['thumbnail'],
                "posttype":post_type,
                "posttime":post_time
            }
            formatted_posts.append(post_data)
        else: continue

    for game in formatted_posts:
        shouldPost = posts.check_post(game)
        if shouldPost == True:
            await displayFreeGame(bot, game)
        else:
            continue

        
async def displayFreeGame(bot, game_info):
    deals_channel = bot.get_channel(settings.discord.freegamedeals)

    free_game_embed = discord.Embed(title="New free game found:",description=f"{game_info['title']}",url=game_info['url'])
    free_game_embed.add_field(name="Platform:", value=f"{game_info['platform']}")
    free_game_embed.add_field(name="Posted:",value=f"{game_info['posttime'].strftime('%m/%d/%y %I:%M%p')} ({settings.server.timezone})")
    free_game_embed.set_footer(text=f"This information was found by me via reddit. If it's inaccurate please inform {settings.discord.botadmin}.")
    if game_info['thumbnail'] == 'default' or game_info['thumbnail'] == 'self':
        pass
    else:
        free_game_embed.set_thumbnail(url=game_info['thumbnail'])
        
    try:
        await deals_channel.send(embed = free_game_embed)
        
    except:
        return errorLogger(thisFunction, f"Couldn't post about the free game: {game_info['title']} from {game_info['url']}")
    functionLogger(thisFunction, f"Posted new free game: {game_info['title']} from {game_info['url']}")