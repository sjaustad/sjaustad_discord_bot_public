## Slash imports
from logging import error
from discord_slash import SlashContext, cog_ext
from discord_slash.context import ComponentContext
from discord_slash.utils.manage_commands import create_option, create_choice
from discord_slash.utils.manage_components import  create_select, create_select_option, create_actionrow, create_button
from discord_slash.model import ButtonStyle
import discord
from logs.logger import errorLogger



class Components:
    def __init__(self):
        self.default_button_style = ButtonStyle.grey
        #self.default_select_style = 
    async def displayButtons(self, ctx, button_items, channel=None, menu_info=None, embed=None, styles=None):
        if channel is None: channel = ctx.channel
        
        ## send hidden message to let discord know we got the interaction
        await ctx.send("Use the menu below", hidden=True)

        buttons = self.createButtons(button_items, styles=styles)
        try:
            if menu_info is None and embed is None: 
                menu_info = "Choose one of the following:"
                return await channel.send(menu_info, components=buttons)
            if embed is not None and menu_info is None:
                menu_info = "Choose one of the following:"
                return await channel.send(embed=embed, components=buttons)
            if embed is not None and menu_info is not None:
                return await channel.send(menu_info, embed=embed, components=buttons)
            elif embed is None and menu_info is not None:
                return await channel.send(menu_info, components=buttons)
            #@self.bot.event
            #async def on_component(ctx: ComponentContext):
            #    return ctx.component['label'].lower()
        except Exception as e:
            errorLogger("displaySelectMenu", f"Failed to display menu: {e}")
            return

    def createButtons(self, button_items, styles=None):
        ## If no style received, set all to default
        if styles is None:
            styles = []
            for x in range(0,len(button_items)):
                styles.append(self.default_button_style)
        ## If a button style is received, set all of them to that style
        elif isinstance(styles, ButtonStyle):
            styles = []
            for x in range(1,button_items):
                styles.append(styles)
        ## If a list of button styles is provided, make as many as you can with given styles and default the rest
        elif isinstance(styles, list):
            for x in range(0, len(button_items)):
                try:
                    if not isinstance(styles[x], ButtonStyle):
                        styles[x] = self.default_button_style
                except IndexError:
                    styles.append(self.default_button_style)

        action_rows = []
        button_options=[]
        x = 1
        style_counter = 0
        for option in button_items:
            button_options.append(create_button(style=styles[style_counter], label=option.title()))
            if x == 5:
                action_rows.append(create_actionrow(*button_options))
                button_options=[]
                x=1
            else:
                x+=1
            style_counter += 1
        action_rows.append(create_actionrow(*button_options))
        return action_rows

    """
    ctx:(req)  context of the interaction
    select_items: (opt) list of string menu items
    channel: (opt) channel object where you want the select menu to be posted
    embed: (opt) embed to send with the menu
    types: (opt) list of types as integers, provide in order of select_items
    min: (opt) integer of minimum number of items that can be picked
    max: (opt) integer of max number of items that can be picked
    placeholder: (opt) default text when user hasn't selected option
    hidden: (opt) don't display the menu to other users
    
    """
    async def displaySelectMenu(self, ctx, select_items, channel=None, menu_info=None, embed=None, types=None, min=1, max=1, placeholder="Click to see options...", hidden=True):
        if channel is None: channel = ctx.channel

        ## defer message until later
        try:
            await ctx.defer()  # I used to send a hidden message --> .send("Use the menu below", hidden=True)
        except: pass
        select_menu = self.createSelectMenu(select_items, types=types, min=min, max=max, placeholder=placeholder)
        try:
            if menu_info is None and embed is None: 
                menu_info = 'Select an option below:'
                if channel is not None:
                    return await channel.send(menu_info, components=select_menu)
                return await ctx.send(menu_info, components=select_menu, hidden=hidden)
            elif embed is not None and menu_info is None:
                menu_info = 'Select an option below:'
                if channel is not None:
                    return await channel.send(embed=embed, components=select_menu)
                return await ctx.send(embed=embed, components=select_menu, hidden=hidden)
            elif embed is not None and menu_info is not None:
                if channel is not None:
                    return await channel.send(menu_info, embed=embed, components=select_menu)
                return await ctx.send(menu_info, embed=embed, components=select_menu, hidden=hidden)
            elif embed is None and menu_info is not None:
                if channel is not None:
                    return await channel.send(menu_info, components=select_menu)
                return await ctx.send(menu_info, components=select_menu, hidden=hidden)

        except Exception as e:
            errorLogger("displaySelectMenu", f"Failed to display menu: {e}")
            return

    def createSelectMenu(self, select_items, types=None, min=1, max=1, placeholder="Select an option from below"):
        if len(select_items) > 25:
            errorLogger("selectMenu","List longer than 25")
        menu_options = []
        for option in select_items:
            menu_options.append(create_select_option(option.title(), value=option))
        menu = create_select(
            options = menu_options,
            placeholder=placeholder,
            min_values=min,
            max_values=max
        )
        return [create_actionrow(menu)]