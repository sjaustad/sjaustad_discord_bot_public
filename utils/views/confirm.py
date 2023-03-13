import discord
# Define a simple View that gives us a confirmation menu

class Confirm:
    class confirm_view(discord.ui.View):
        def __init__(self, confirm_text, cancel_text):
            super().__init__()
            self.value = None
            if confirm_text is None:
                self.confirm_text="Confirmed"
            else:
                self.confirm_text = confirm_text
            if cancel_text is None:
                self.cancel_text="Cancelled"
            else:
                self.cancel_text=cancel_text
        


        # When the confirm button is pressed, set the inner value to `True` and
        # stop the View from listening to more input.
        # We also send the user an ephemeral message that we're confirming their choice.
        @discord.ui.button(label='Confirm', style=discord.ButtonStyle.green)
        async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
            #await interaction.response.send_message(self.confirm_text, ephemeral=True)
            self.value = True
            self.stop()


        # This one is similar to the confirmation button except sets the inner value to `False`
        @discord.ui.button(label='Cancel', style=discord.ButtonStyle.grey)
        async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
            #await interaction.response.send_message(self.cancel_text, ephemeral=True)
            self.value = False
            self.stop()

    class cancel_view(discord.ui.View):
        def __init__(self, cancel_text):
            super().__init__()
            self.value = None

            if cancel_text is None:
                self.cancel_text="Cancelled"
            else:
                self.cancel_text=cancel_text
        # This one is similar to the confirmation button except sets the inner value to `False`
        @discord.ui.button(label='Cancel', style=discord.ButtonStyle.grey)
        async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_message(self.cancel_text, ephemeral=True)
            self.value = False
            self.stop()


    ## Needs an interaction for app commands or ctx for message-based commands 
    ## Also requires either message text or an embed
    ## Optionally can accept text to display during confirmation and cancellation of request
    async def display(interaction:discord.Interaction =None, channel=None, text=None, embed=None, cancel_button_only = False, ephemeral=True, cancel_text=None, confirm_text=None, confirm_button_text="Confirm", cancel_button_text="Cancel", edit_original=False):
        if text is None and embed is None: print("You need to supply message text or an embed!")
        if interaction is None and channel is None: print("You need to supply an interaction or a channel.")
        
        if cancel_button_only is True:
            confirm_view = Confirm.cancel_view(cancel_text)
            confirm_view.cancel.label = cancel_button_text
        else:
            confirm_view = Confirm.confirm_view(confirm_text, cancel_text)
            confirm_view.cancel.label = cancel_button_text
            confirm_view.confirm.label = confirm_button_text
       
        if edit_original is True:
            await interaction.edit_original_response(embed=embed, view=confirm_view)
        else:

            if interaction is not None:
                if text is not None:
                    try:
                        await interaction.response.send_message(text, view=confirm_view, ephemeral=ephemeral)
                    except:
                        await interaction.followup.send(text, view=confirm_view, ephemeral=ephemeral)
                elif embed is not None:
                    try:
                        await interaction.response.send_message(embed=embed, view=confirm_view,ephemeral=ephemeral)
                    except:
                        await interaction.followup.send(embed=embed, view=confirm_view,ephemeral=ephemeral)
                

            else:
                if text is not None:
                    confirm_message = await channel.send(text, view=confirm_view)
                if embed is not None:
                    confirm_message = await channel.send(embed=embed, view=confirm_view)
        try:
            await confirm_view.wait() ## When using this with user_input text class there seems to be a problem with this line
        except:
            pass

        ## remove the buttons
        if interaction is not None:
            await interaction.edit_original_response(view=None)
        else:
            confirm_message.edit(view=None)
            
        return confirm_view.value
        