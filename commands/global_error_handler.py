import discord
from discord.ext import commands
from discord import app_commands, Interaction
from discord.app_commands import AppCommandError, Command, ContextMenu
from typing import Union

async def global_app_command_error_handler(bot: commands.Bot):
    @bot.tree.error
    async def app_command_error(
            interaction: Interaction,
            #command: Union[Command, ContextMenu],
            error: AppCommandError
    ):
        # print(interaction, command, error)
        if isinstance(error, app_commands.CommandInvokeError):
            print(error.original, error.command)
        elif isinstance(error, app_commands.TransformerError):
            print(error.value, error.type, error.transformer)
        elif isinstance(error, app_commands.CheckFailure):
            if isinstance(error, app_commands.NoPrivateMessage):
                pass
            elif isinstance(error, app_commands.MissingRole):
                print(error.missing_role)
            elif isinstance(error, app_commands.MissingAnyRole):
                roles_text = "(Requires: "
                if len(error.missing_roles) > 1:
                    for role in error.missing_roles:
                        if error.missing_roles[-1] == role:
                            roles_text += "or " + role
                        else:
                            roles_text += role + ", "
                else:
                    roles_text += error.missing_roles[0]
                roles_text += ")"
                await interaction.response.send_message(f"{interaction.user.mention}, you don't have permission to use this command! {roles_text}", ephemeral=True)
                # for role in error.missing_roles:
                #     print(role)

            elif isinstance(error, app_commands.MissingPermissions):
                for permission in error.missing_permissions:
                    print(permission)
            elif isinstance(error, app_commands.BotMissingPermissions):
                for permission in error.missing_permissions:
                    print(permission)
            elif isinstance(error, app_commands.CommandOnCooldown):
                print(error.cooldown, error.retry_after)
        elif isinstance(error, app_commands.CommandLimitReached):
            print(error.type, error.guild_id, error.limit)
        elif isinstance(error, app_commands.CommandAlreadyRegistered):
            print(error.name, error.guild_id)
        elif isinstance(error, app_commands.CommandSignatureMismatch):
            print(error.command)
        elif isinstance(error, app_commands.CommandNotFound):
            print(error.name, error.parents, error.type)


async def setup(bot):
    await global_app_command_error_handler(bot=bot)
