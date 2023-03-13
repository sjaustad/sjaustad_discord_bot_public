import discord, os, asyncio
from discord.ext import commands

with open('./settings/base_dir.txt', 'w') as file:
    file.write(os.getcwd())

#Declare Server intents
intents = discord.Intents.all()
intents.members = True


# Start up Discord client
print("Starting discord bot")


from utils.bot import MyBot
async def main():
    from utils.database import connector_async
    redis_async = connector_async.Async_Redis()
    await redis_async.create_pool()
    
    bot = MyBot(redis_async)
    async with bot:        await bot.start(bot.settings.discord.apitoken)


asyncio.run(main())