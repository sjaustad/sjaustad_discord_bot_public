from ast import Bytes
from tarfile import DEFAULT_FORMAT
import discord, traceback, asyncio, os
from discord import app_commands
from discord.ext import commands
from datetime import datetime

from urllib import request

## experimental image resizing:
#from PIL import Image
#from io import BytesIO
#import requests

class Upload_cog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="upload", description="Upload files larger than Discord's pathetic limit")
    async def upload(self, interaction: discord.Interaction):
        ## Create a new Drive folder and get the share link
        folder_info = await self.bot.DriveAPI.create_folder(interaction.user)
        link  = await self.bot.DriveAPI.share_folder(folder_info)

        #upload_message = await interaction.response.send_message(f"{interaction.user.mention} upload your file to this URL: {link}", ephemeral=True)
        timeout=100
        upload_link_embed = discord.Embed(title=f"{interaction.user.name}, upload your file here.", url=link)
        upload_link_embed.add_field(name=f"Waiting {timeout} seconds for upload to complete...", value="\u200b")

        async def check_status(bot):
            check_interval = 5 #10 seconds
            uploaded=False
            counter = 0
            while uploaded is False:
                uploaded = await bot.DriveAPI.check_upload_status(folder_info)  
                await asyncio.sleep(check_interval)
                counter += 1
                cancel_upload = False
            return uploaded

        # await upload_message.add_reaction('❌')
        from utils.views.confirm import Confirm
        

        cancel_task = asyncio.create_task(Confirm.display(interaction=interaction, embed = upload_link_embed, cancel_button_only=True, cancel_text='File upload cancelled'))
        check_upload_task = asyncio.create_task(check_status(self.bot))
        
        success, no_response = await asyncio.wait([check_upload_task, cancel_task], return_when=asyncio.FIRST_COMPLETED, timeout=timeout)


        for task in no_response:
            task.cancel()
        for task in success:
            try:
                result = task.result()
            except asyncio.TimeoutError:
                pass

        uploaded = result


        if uploaded is False:
            pass
            #await ctx.send(f"{ctx.author.mention}, did not find an uploaded file cancelling request.")
        else:
            await self.bot.DriveAPI.remove_writer_permissions(folder_info)
            dl_link = "https://drive.google.com/uc?export=download&id=" + uploaded['file_id']

            ## Create a nice looking embed
            upload_embed = discord.Embed(title=f"New file upload", description=f"from {interaction.user.mention}")
            upload_embed.add_field(name="Upload date",value=f"{datetime.now().strftime('%m/%d/%y %I:%M%p')}")
            upload_embed.add_field(name="File name",value=f"{uploaded['file_name']}")
            upload_embed.add_field(name="Link",value=dl_link, inline=False)

            ## couldn't get this working
            ## Also, pretty sure this would be a security vulnerability anyways

            # ## Is it an image?
            # approved_images_ext = ['.jpg','.jpeg','.png','.gif','.webp']
            # extension = os.path.splitext(uploaded['file_name'])[1]
            # if extension in approved_images_ext:
            #     image_file = requests.get(dl_link)
            #     image_file = request.urlretrieve(dl_link, 'resize_file.img')
            #     Image.MAX_IMAGE_PIXELS = 999999999
            #     #pil_image = Image.open(BytesIO(image_file.content))
            #     pil_image = Image.open('resize_file.img')
            #     pil_image.mode = 'RGBA'
            #     ## rescale to 1000 width or height
            #     if pil_image.height > 1000 or pil_image.width > 1000:
            #         if pil_image.height > pil_image.width:
            #             ratio = pil_image.height/pil_image.width
            #             new_height = 1000
            #             new_width = round(new_height / ratio)
            #         else:
            #             ratio = pil_image.width/pil_image.height
            #             new_width = 1000
            #             new_height = round(new_width / ratio)
            #         pil_image = pil_image.resize((new_height, new_width), Image.ANTIALIAS)
            #         upload_embed.set_image(url=dl_link)

            await interaction.followup.send(embed=upload_embed)


        pass
    
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Upload_cog(bot))