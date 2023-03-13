import asyncio, datetime
from settings.server_settings import settings
settings = settings()
## asyncio.sleep() sets the interval in seconds before running the loop again
class loops:
    def __init__(self, bot):
        ## Create discord tasks from class functions

        #bot.loop.create_task(self.monitorEvents(bot))
        bot.loop.create_task(self.checkNewPosts(bot))
        #bot.loop.create_task(self.checkListingStatus(bot))
        bot.loop.create_task(self.checkVoiceChannelStatus(bot))
        bot.loop.create_task(self.getMemeofDayRoutine(bot))
        bot.loop.create_task(self.midnightChannel(bot))        

    async def monitorEvents(self, bot):
        await bot.wait_until_ready()
        from loop_functions.CheckEvents import CheckEvents
        while True:
            await CheckEvents(bot)
            await asyncio.sleep(60)

    async def checkNewPosts(self, bot):
        await bot.wait_until_ready()
        from loop_functions.CheckFreeGames import checkFreeGames
        while True:
            await checkFreeGames(bot)
            await asyncio.sleep(1800)

    async def checkListingStatus(self, bot):
        await bot.wait_until_ready()
        from loop_functions.ScanMarketplaceListings import checkListings
        while True:
            await checkListings()
            await asyncio.sleep(60)

    async def checkVoiceChannelStatus(self, bot):
        await bot.wait_until_ready()
        from loop_functions.CheckVoiceChannels import checkVoiceChannels
        while True:
            await checkVoiceChannels(bot)
            await asyncio.sleep(60)

    async def getMemeofDayRoutine(self, bot):
        await bot.wait_until_ready()
        from loop_functions.GetMemeofDay import getMemeofDay
        while True:
            await getMemeofDay(bot)
            await asyncio.sleep(1800)

    async def midnightChannel(self, bot):
        await bot.wait_until_ready()
        from loop_functions.CheckMidnightStatus import openMidnightChannel
        while True:
            current_time = datetime.datetime.now()
            midnight = datetime.datetime(current_time.year,current_time.month,current_time.day,0,0)
            cutoff_time = datetime.datetime(current_time.year,current_time.month,current_time.day,4,0)
            if current_time > midnight and current_time < cutoff_time:
                open_that_channel = True
                await openMidnightChannel(bot, open_that_channel, settings)
            else:
                open_that_channel = False
                await openMidnightChannel(bot, open_that_channel, settings)
            await asyncio.sleep(60)