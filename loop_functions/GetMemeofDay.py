import os, discord, asyncio, requests, json, re
from datetime import datetime
from settings.server_settings import settings
settings = settings()

from logs.logger import errorLogger, functionLogger

from utils.database.calls.reddit_posts import Reddit
posts = Reddit()

thisFunction = "getMemeofDay"
async def getMemeofDay(bot):
    checkTime = postOnceDay()
    if checkTime == False: return

    url = "https://www.reddit.com/r/DankMemes/top/.json?limit=3"
    reddit_info_raw = requests.get(url, headers = {'User-agent': 'your bot 0.1'})
    reddit_info = json.loads(reddit_info_raw.text)

    formatted_posts = []    
    for post in reddit_info['data']['children']:
        if post['data']['stickied'] == True:
            continue

        post_time = datetime.fromtimestamp(post['data']['created_utc'])

        post_data = {
            "title":post['data']['title'],
            "url":post['data']['url'],
            "pic_url":post['data']['url_overridden_by_dest'],
            "id":post['data']['id'],
            "posttype":"meme",
            "posturl":post['data']['permalink'],
            "thumbnail":post['data']['thumbnail'],
            "posttime":post_time,
            "ratio":post['data']['upvote_ratio'],
            "upvotes":post['data']['ups']
        }
        formatted_posts.append(post_data)


    if len(formatted_posts) <= 0:
        return

    meme = formatted_posts[0]
    #for meme in formatted_posts:
    

    shouldPost = posts.check_post(meme)
    if shouldPost == True:
        await displayMeme(bot, meme)
        
    #else:
    #    continue

def postOnceDay():
    current_time = datetime.now()
    if current_time.hour < 17 and current_time.hour >= 16:
        return True
    else: return False

async def displayMeme(bot, meme):
    meme_channel = bot.get_channel(settings.discord.memechannel)

    full_url =  "https://reddit.com" + meme['posturl']
    meme_embed = discord.Embed(title="Today's top meme:",description=f"{meme['title']}", url=full_url)
    meme_embed.set_image(url=meme['pic_url'])
    meme_embed.add_field(name="Total upvotes",value=meme['upvotes'])
    meme_embed.add_field(name="Upvote Percentage",value=f"{meme['ratio'] * 100}%")
    meme_embed.set_footer(text=f"This is the top meme today from Dankmemes. Downvote if it sucks worse then WW84, upvote if it's as hot as Shrek.")

    try:
        message = await meme_channel.send(embed=meme_embed)
    except:
        return errorLogger(thisFunction, f"Couldn't post top meme: {meme['title']} from {meme['url']}")
    
    try:
        await message.add_reaction("⬆️")
        await message.add_reaction("⬇️")
    except:
        return errorLogger(thisFunction, f"Couldn't add reactions: {meme['title']} from {meme['url']}")
    functionLogger(thisFunction, f"Posted top meme: {meme['title']} from {meme['url']}")