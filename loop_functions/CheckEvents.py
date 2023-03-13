import os, discord, asyncio
from dateutil.parser import parse
from dbqueries.EventFunctions import getAllEvents, deleteEvent, changeCompletion
from settings.server_settings import settings
settings = settings()
from gen_functions.LotteryFunctions import startDrawing
from gen_functions.DisplayLongList import displayLongList
from datetime import datetime
from dbqueries.UserAttributes import getServerAttribute, removeAllServerAttributes
from commands_old.public_commands.vote import getElectionResults

async def CheckEvents(bot):
    events = getAllEvents()
    for event in events:
        event_time = parse(event['eventTime'])
        current_time = datetime.now()
        diff = event_time - current_time
        minutes_to_event = diff.seconds / 60

        ## If the time difference is 1 or over, than it can't be today so
        ## skip everything else
        if diff.days >= 1:
            continue
        else:
            if minutes_to_event < event['eventNotify'] or diff.days < 0:
                ## Check to make sure the event hasn't completed yet
                ## and notify people

                ## Get the event channel object and the event message object
                ## using the channel
                event_channel = bot.get_channel(settings.discord.lotterychannel)
                
                try:
                    event_message = await event_channel.fetch_message(event['eventMessageID'])
                except:
                    ## Message must not exist anymore, so delete the event
                    deleteEvent(event['eventName'].replace("'","''"))
                    

                if event['completed'] == False:
                    ## If it is a lottery, move one to that function
                    if event['eventType'] == "lottery": 
                        await startDrawing(bot, event)
                        continue
                    
                    if event['eventType'] == "election":
                        for guild in settings.guild_list:

                            event_channel = bot.get_channel(guild.server.channels.eventchannel)
                            ## post results
                            #test_channel = bot.get_channel(settings.discord.testchannel)
                            results = await getElectionResults(event,bot=bot)
                            election_info = getServerAttribute(event['eventName'], "info")
                            election_embed = discord.Embed(title=f"The following election has ended: {event['eventName']}", description=f"Below are the results of the election. Top {election_info['positions']} are the newly elected candidates.")
                            await event_channel.send(embed=election_embed)
                            headers = ["[Name]","[Votes]"]
                            await displayLongList(event_channel, results, headers, auto_sort=False)

                        ## Clean up
                        removeAllServerAttributes(event['eventName'])
                        changeCompletion(event['eventName'], True)
                        continue
                    
                    ## If it is a formal event, get list of people and message them
                    if event['eventType'] != "informal":
                        ## Get the list of members
                        notify_users, not_attending = await getEventMembers(bot, message=event_message)
                        await messageAttendees(bot, notify_users, event, minutes_to_event)
                        changeCompletion(event['eventName'], True)
                    ## if informal event, just send a quick notification
                    else:
                        await announceInformalEvent(bot,event,event_message, event_channel)
                        changeCompletion(event['eventName'], True)
                    ## Update the embed that the event has started
                    event_embed = event_message.embeds[0]
                    event_embed.add_field(name="Event Started",value=f"**YES**")
                    await event_message.edit(embed=event_embed)
                else:
                    ## Instead of deleting event right away, we'll wait until the next day
                    ## Get midnight of the event date and if it is any time during the next
                    ## day it will automatically delete the event from the database and the 
                    ## message
                    midnight_eventdate = datetime.combine(event_time, datetime.min.time())
                    midnight_diff = midnight_eventdate - current_time

                    if midnight_diff.days <= -2:
                        await event_message.delete()
                        deleteEvent(event['eventName'])

async def announceInformalEvent(bot, event, event_message, event_channel):
    user = bot.get_user(event['eventOwner'])
    announcment_embed = discord.Embed(title=f"Reminder for {event['eventName']}", description=f"This event was created by {bot.get_user(event['eventOwner']).name} and starts now.")
    announcment_embed.add_field(name="Event Description", value=f"{event['eventDescription']}")

    announcement_message = await event_channel.send(embed=announcment_embed)
    await asyncio.sleep(60)
    return await announcement_message.delete()

async def messageAttendees(bot, user_list, event, time_left):
    time_left = round(time_left)
    event_date = parse(event['eventTime'])

    ## Setup the embed to send to users
    published_event = discord.Embed(title=f"Reminder for {event['eventName']}", description=f"You signed up for this event created by {bot.get_user(event['eventOwner']).name}", color=discord.Color.orange())
    published_event.add_field(name="Event Type", value=f"{event['eventType']}",inline=True)

    if event['eventNotify'] == 0:
        published_event.add_field(name="Time", value=f"Starts **now** at {event_date.strftime('%m/%d/%y %I:%M%p')} ({settings.server.timezone})",inline=True)
    else:
        published_event.add_field(name="Time", value=f"Starts in **{time_left} minutes** at {event_date.strftime('%m/%d/%y %I:%M%p')} ({settings.server.timezone})",inline=True)
    published_event.add_field(name="Description", value=f"{event['eventDescription']}",inline=False)

    ## Send a DM to every user who signed up for the event
    for user in user_list:
        dm_chat = await user.create_dm()
        await dm_chat.send(embed=published_event)

async def getEventMembers(bot, message=None, message_ID=None):
    for guild in settings.guild_list:
        ## If a message is not given, then get the message by ID
        if message is None:
            event_channel = bot.get_channel(guild.server.channels.eventchannel)
            event_message = await event_channel.fetch_message(message_ID)
        ## Getting a message object is preferred so it you give both it will
        ## try from message first
        else:
            event_message = message
        attending_users = []
        not_attending_users = []
        ## Check all reactions that are check mark and exclude the bot user from the notification list
        for reaction in event_message.reactions:
            if reaction.emoji == "✅":
                async for user in reaction.users():
                    if not user.id == bot.user.id:
                        attending_users.append(user)
            elif reaction.emoji == "❌":
                async for user in reaction.users():
                    if not user.id == bot.user.id:
                        not_attending_users.append(user)
        return attending_users, not_attending_users