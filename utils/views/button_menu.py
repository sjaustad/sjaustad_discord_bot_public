import discord

class InteractionMenu:
    def __init__(self, bot):
        self.bot = bot

    ## returns a discord.ui.View object with buttons in the .children attribute
    ## requires a list of menu_options (usually strings)
    ## can optionally have a cancellation button
    async def generate_view(self, menu_options, interaction: discord.Interaction=None, cancel_button=True):
        ## create view
        menu_view = InteractionMenu._MenuView()

        ## make and add the custom buttons
        for option in menu_options:
            menu_view.add_item(InteractionMenu.custom_button(option, menu_options.index(option), self.bot, interaction))
        
        if cancel_button is True:
            ## Add a cancel button
            menu_view.add_item(InteractionMenu.custom_button("Cancel", (len(menu_options)+1), self.bot, interaction, style=discord.ButtonStyle.red))
        return menu_view
    
    ## Takes a list of discord.ui.Button objects
    async def generate_view_advanced(self, button_list, bot, interaction: discord.Interaction=None, cancel_button=True):
        ## create view
        menu_view = InteractionMenu._MenuView()

        ## make and add the custom buttons
        for button in button_list:
            button.menu_message = interaction
            button.value=button.label
            button.index=button_list.index(button)
            button.bot = bot
            menu_view.add_item(button)
        
        if cancel_button is True:
            ## Add a cancel button
            menu_view.add_item(InteractionMenu.custom_button("Cancel", (len(button_list)+1), self.bot, interaction, style=discord.ButtonStyle.red))
        return menu_view


    async def allow_original_menu_updates(self, view: discord.ui.View, menu_message: discord.Message):
        for child in view.children:
            child.menu_message = menu_message

    class _MenuView(discord.ui.View):
        def __init__(self,):
            super().__init__()

    class custom_button(discord.ui.Button):
        def __init__(self, label, index, bot, interaction, style: discord.ButtonStyle=discord.ButtonStyle.grey):
            super().__init__()
            self.bot = bot
            self.value = label
            self.label = label
            self.index = index
            self.menu_message = interaction
            self.style = style
