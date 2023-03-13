import asyncio
from utils.views.confirm import Confirm

class UserInput:
    def __init__(self, bot):
        self.bot = bot

    async def get_text_response(self, embed, interaction=None, channel=None, user=None,timeout=60, delete_response=True , message=None, firstTime=True, timeout_message=None, hide_display=False, custom_footer=None):
        """ This function asks a user for text information and returns a dictionary of the user's response

        Args:
            embed (discord.Embed): _description_
            interaction (discord.Interaction, required if no channel): _description_. Defaults to None.
            channel (discord.Channel, required if no interaction): _description_. Defaults to None.
            user (discord.User, required): _description_. Defaults to None.

            timeout (int, optional): _description_. Defaults to 60.
            delete_response (bool, optional): _description_. Defaults to True.
            message (discord.Message, optional): _description_. Defaults to None.
            firstTime (bool, optional): _description_. Defaults to True.
            timeout_message (str, optional): _description_. Defaults to None.
            hide_display (bool, optional): _description_. Defaults to False.
            custom_footer (str, optional): _description_. Defaults to None.

        Returns:
            dict: user response

            user_message = None # user response timed out
            user_message = discord.Message # user returned message
            user_message = False # user cancelled input

            response_dict={
                'bot_message':message,  # Previous message if stringing multiple responses together
                'user_message':None, # message that the user sent to the bot
                'user_text':None, # text content of the above message, also user_message.content
                'status':'timeout' # status of the response, whether it was a successful, cancelled, or timeout
            }
        """
        ## required parameter check
        if user is None: return print('No user supplied for get_text_response!')
        if channel is None and interaction is None: return print('No channel or interaction supplied for get_text_response!')
        

        if interaction:
            try:
                await interaction.response.defer(ephemeral=True)

            except: pass
        if embed.footer.text is None:
            if custom_footer is not None:
                embed.set_footer(text=custom_footer)
            else:
                embed.set_footer(text=f"Waiting {timeout} seconds for your reply.")
        else:
            if custom_footer is not None:
                embed.set_footer(text=custom_footer)
            else:        
                new_footer = embed.footer.text + f" Waiting {timeout} seconds for your reply."
                embed.set_footer(text=new_footer)


        ## ensures that the text response received is only from the person who intiated the command
        def textResponse(m):
            return m.author == user and channel == m.channel

        ## in some cases we may want to hide the button and prompt asking for input
        ## this is useful in cases like transcribe where we don't want the bot asking the user
        ## for input every time the person gives a typed response
        if hide_display is False:
            if interaction:
                interaction_task = asyncio.create_task(Confirm.display(interaction=interaction, embed=embed,ephemeral=True))
            else:
                interaction_task = asyncio.create_task(Confirm.display(channel=channel, embed=embed,ephemeral=True))
            tasks = [interaction_task, self.bot.wait_for('message', timeout=timeout, check=textResponse)]
        else:
            tasks = [self.bot.wait_for('message', check=textResponse)]

        ## start the tasks above and wait for the amount specified in timeout
        user_responses, no_response = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED, timeout=timeout)

        ## if there are no user responses then the interaction timed out
        if len(user_responses) <= 0:
            timeout=True
        else: timeout=False

        ## cancel all the tasks that didn't receive a response
        for task in no_response:
            task.cancel()

        ## if any responses, get the results and store them to user_response
        for task in user_responses:
            try:
                user_response = task.result()
            except asyncio.TimeoutError:
                timeout = True
            else:
                timeout = False
        
        ## special case for timeout since there will be no user_responses
        if timeout == True:
            response_dict={
                'bot_message':message,
                'user_message':None,
                'user_text':None,
                'status':'timeout'
            }
            if timeout_message is None:
                if interaction:
                    await interaction.followup.send(f"{user.mention}, reply timed out.",ephemeral=True)
                else:
                    await channel.send(f"{user.mention}, reply timed out.")
            else:
                if interaction:
                    await interaction.followup.send(f"{user.mention} {timeout_message}",ephemeral=True) 
                else:
                    await channel.send(f"{user.mention} {timeout_message}")
            return response_dict

        ## otherwise we will return the user_response
        if user_response:
            response_dict = {
                'bot_message':message,
                'user_message':user_response,
                'user_text':user_response.content,
                'status':'success'
            }
        else:
            response_dict = {
                'bot_message':message,
                'user_message':False,
                'user_text':False,
                'status':'cancel'
            }

        ## we try to automatically clear the user's text message unless told not to
        if delete_response is True:
            try: 
                await user_response.delete()
            except:
                pass # cannot delete messages in private channel
        return response_dict
