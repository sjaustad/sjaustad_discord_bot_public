import os, discord


async def openMidnightChannel(bot, status, settings):
    midnight_channel = bot.get_channel(settings.discord.midnightchannel)
    current_permissions = midnight_channel.overwrites_for(bot.guilds[0].default_role)

    if status is False and (current_permissions.read_messages is True or current_permissions.read_messages is None):
        await midnight_channel.set_permissions(bot.guilds[0].default_role, read_messages=False)
    elif status is True and (current_permissions.read_messages is False or current_permissions.read_messages is None): 
        await midnight_channel.set_permissions(bot.guilds[0].default_role, read_messages=True)