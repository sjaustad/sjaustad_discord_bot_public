"""
This function allows you to send in a list of items and headers to output a neat table in discord. It will 
also provide reactions that allow the user to go back and forth between pages.

Parameters:
ctx: always required. This is the current user context

list_items: needs to be preformatted array of arrays that match the headers. For example: if you have the
header array ['name','dob','city'] then you would send in array like this: [['joe','01/01/1980','Detroit'],['jack','01/02/1983','Memphis']]

headers: must match the format for all of the data cells and needs to be the same length as each set of data.

message: you can specify an existing message. If you do this, the function will try and replace the message

sort: integer value that will sort the list_items by the number in the array given. Default is 0 so it will
sort by the first elements of each array. In the example above, the default would sort by name in alphabetical order

items_per_page: how many items will be displayed for each page

"""


import os, discord, asyncio
from tabulate import tabulate
from operator import itemgetter
from logs.logger import functionLogger

thisFunction = "DisplayLongList"
async def displayLongList(ctx, list_items, headers, source_embed=None, message=None, sort=0, items_per_page=15,auto_sort=True, hidden=False):
    if auto_sort is True:
        sorted_list = sorted(list_items, key=itemgetter(sort))
    else: sorted_list = list_items
    x=1
    single_table=[]
    tables = []
    for item in sorted_list:
        if x > items_per_page:
            table_str = "```ini" + "\n" + tabulate(single_table, headers, tablefmt="plain") + "```"
            tables.append(table_str)
            single_table=[]
            x=0
        single_table.append(item)
        x += 1
    table_str = "```ini" + "\n" + tabulate(single_table, headers, tablefmt="plain") + "```"
    tables.append(table_str)

    if len(tables) == 0: return functionLogger(thisFunction, "asked to display list, but didn't generate any tables")
    if len(tables) == 1:
        if source_embed is not None:
            source_embed.add_field(name="\u200b",value=tables[0], inline=False)
            list_message = await ctx.send(embed=source_embed)
        else:
            list_message = await ctx.send(tables[0])
        return_obj = {
            'message':list_message
        }
    else:
        current_index = 0
        list_message = await ctx.send(tables[current_index])
        await_reaction = True
        first_time = True
        while await_reaction is True:
            user_response = await waitForReactions(ctx, list_message, first=first_time)
            await_reaction = user_response['wait']
            try:
                if user_response['response'] == "next":
                    await list_message.delete()
                    current_index += 1
                    if current_index <= 0 or current_index > len(tables) - 1: 
                        current_index = 0
                        first_time=True
                    else: first_time = False
                    list_message = await ctx.send(tables[current_index])
            except: return

            if user_response['response'] == "back":
                await list_message.delete()
                current_index -= 1
                if current_index <= 0 or current_index > len(tables) - 1:
                    current_index = 0
                    first_time=True
                else: first_time = False
                list_message = await ctx.send(tables[current_index])

            
                  
    return return_obj

def makeList(list_items, headers, source_embed=None, message=None, sort=0, items_per_page=15,auto_sort=True):
    if auto_sort is True:
        sorted_list = sorted(list_items, key=itemgetter(sort))
    else: sorted_list = list_items

    single_table=[]


    return "```ini" + "\n" + tabulate(sorted_list, headers, tablefmt="plain") + "```"    

async def waitForReactions(ctx, message, first=False):
    if first is True:
        await message.add_reaction('▶️')
    else:
        await message.add_reaction('◀️')
        await message.add_reaction('▶️')
        

    def check(reaction, user):
        if user == ctx.author and str(reaction.emoji) == '▶️' or user == ctx.author and str(reaction.emoji) == '◀️':
            return True

    try:
        reaction, user = await ctx.bot.wait_for('reaction_add', timeout=300, check=check)
    except asyncio.TimeoutError:
        return_obj={
            'wait':False
        }
        return return_obj
    else:
        if str(reaction.emoji) == '▶️':
            return_obj = {
                'response':'next',
                'message':message,
                'wait':True
            }
            return return_obj
        elif str(reaction.emoji) == '◀️':
            return_obj = {
                'response':'back',
                'message':message,
                'wait':True
            }
            return return_obj