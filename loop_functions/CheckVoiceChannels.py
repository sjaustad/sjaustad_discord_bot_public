import os, discord,datetime
from dateutil.parser import parse
from settings.server_settings import settings
settings = settings()
from logs.logger import errorLogger


from utils.database.calls.users import Users
users=Users()

thisCommand = "checkVoiceChannels"
async def checkVoiceChannels(bot):
    voice_channels = users.get_one_attribute_all_users("voice_channel")
    if len(voice_channels) <= 0: return

    current_time = datetime.datetime.now()
    for channel in voice_channels:
        channel = channel['value']
        creation_time = parse(channel['created'])
        time_diff = current_time - creation_time
        if time_diff.seconds + time_diff.days * 86400 >= settings.discord.voice_channel_timeout * 60 * 60:
            thisChannel = bot.get_channel(channel['channelid'])

            ## If there are people in the voice channel, do not delete
            try:
                user_list = list(thisChannel.voice_states.keys())
            except AttributeError: user_list=[]
            if len(user_list) > 0: continue

            ## Delete channel
            try:
                await thisChannel.delete()
            except:
                errorLogger(thisCommand, f"Failed to delete channel {channel['name']} - id: {channel['channelid']}. Removing database entry.")
                
            ## Delete user attribute
            users.remove_attribute(channel['userid'], "voice_channel")