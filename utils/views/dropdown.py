import discord

class DropdownMenu():
    class ui(discord.ui.Select):
        def __init__(self, option_list, placeholder=None, min_values=1, max_values=1):
            super().__init__(placeholder=placeholder, min_values=min_values, max_values=max_values, options=option_list)
            self.dropdown_view = _DropdownView()
            self.dropdown_view.add_item(self)
    
    async def display(interaction, option_list, dropdown_descriptor=None, embed=None, bot=None, placeholder=None, min_values=1, max_values=1, storage=None):
        if dropdown_descriptor is None and embed is None: return False

        dropdown_ui = DropdownMenu.ui(option_list, placeholder, min_values, max_values)
        if bot:
            dropdown_ui.bot = bot
        if storage:
            dropdown_ui.storage = storage
        dropdown_view = _DropdownView()
        dropdown_view.add_item(dropdown_ui)
        if dropdown_descriptor:
            try:
                interaction = await interaction.followup.send(content=dropdown_descriptor, view=dropdown_view, ephemeral=True)
            except:
                await interaction.response.send_message(dropdown_descriptor, view=dropdown_view, ephemeral=True)
        elif embed:
            try:
                interaction = await interaction.followup.send(embed=embed, view=dropdown_view, ephemeral=True)
            except:
                await interaction.response.send_message(embed=embed, view=dropdown_view, ephemeral=True)            
        return interaction
    

class _DropdownView(discord.ui.View):
    def __init__(self):
        super().__init__()
        # Adds the dropdown to our view object.
        #self.add_item(select)



"""
class DropDown:
    class _Dropdown_Select(discord.ui.Select):
        def __init__(self, placeholder, option_list, min_values, max_values):
            super().__init__(placeholder=placeholder, min_values=min_values, max_values=max_values, options=option_list)
            self.add_item(DropDown._Dropdown_Select(placeholder, option_list, min_values, max_values))

    class DropdownView(discord.ui.View):
        def __init__(self, placeholder, option_list, min_values=1, max_values=1):
            super().__init__()
            # Adds the dropdown to our view object.
            self.add_item(DropDown._Dropdown_Select(placeholder, option_list, min_values, max_values))
"""
