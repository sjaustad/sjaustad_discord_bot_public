import discord
class CheckRole:
    def __init__(self):
        pass

    def check_role(self, settings, guild: discord.Guild, user: discord.User, role_list: list):
        authorized = False
        guild_roles = getattr(settings.guilds, str(guild.id)).server.roles
        matching_user_roles = [role for role in role_list for user_role in user.roles if user_role.name.lower() == getattr(guild_roles, role).lower()]
        
        if len(matching_user_roles) > 0:
            authorized = True
            
        return authorized
    
    async def not_auth_message(self, interaction: discord.Interaction= None, channel=None):
        if interaction:
            try:
                await interaction.response.send_message(f"You are not authorized to use this command.", ephemeral=True)
            except:
                await interaction.followup.send(content=f"You are not authorized to use this command.", ephemeral=True)