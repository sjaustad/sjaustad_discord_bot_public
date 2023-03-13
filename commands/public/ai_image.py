
import asyncio, pickle, datetime
from distutils.util import check_environ
from re import L
from socket import BTPROTO_RFCOMM
from urllib import request
import discord
from discord import app_commands
from discord.ext import commands
from dateutil import parser
import time, os

from PIL import Image
Image.MAX_IMAGE_PIXELS = 999999999

from settings.server_settings import settings
settings = settings()

from utils.views.button_menu import InteractionMenu
from utils.database.calls.ai_image_queue import Queue

## Role Auth import
from utils.auth.check_role import CheckRole
auth = CheckRole()

## to do:
## why is img2img doing 35 ddim steps
## [done] add parent field to more info
## buttons not showing on completion
## ai variant from web upscale not working

class AI_image_gen_cog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.queue_db = Queue(bot.redis)

        ## if images are larger than this value we don't process them
        ## the GPU will run out of memory
        self.max_upscale_height = 2200
        self.max_upscale_width = 2200

        ## variants seem to not work if they're over 512x512 on my GPU
        self.max_variant_height = 512
        self.max_variant_width = 512

        ## Establish folders as needed for image generation
        if not os.path.exists("plugins/ai_image_generator"):
            os.mkdir("plugins/ai_image_generator")
        if not os.path.exists("plugins/ai_image_generator/output_images"):
            os.mkdir("plugins/ai_image_generator/output_images")
        if not os.path.exists("plugins/ai_image_generator/_tmp"):
            os.mkdir("plugins/ai_image_generator/_tmp")
        if not os.path.exists("plugins/ai_image_generator/storage"):
            os.mkdir("plugins/ai_image_generator/storage")
        self.temp_dir = "plugins/ai_image_generator/_tmp"
    

    ## command for generating new images using the AI image engine Stable Diffusion
    @app_commands.command(name="ai", description="Generate AI images. Make sure to use NSFW channel for those requests or you could be banned.")
    async def image_gen(self, interaction: discord.Interaction, prompt: str, ddim_steps: int=50, n_iter:int=2, seed:str=None, samples:int=2, width:int=512, height:int=512):
        ## notify the user of their prompt immediately in case something happens to it
        await interaction.response.send_message(f"Preparing to send {prompt} to queue", ephemeral=True)
        ## check if server is up
        if not await self.check_server_status(interaction, prompt=prompt): return

        ## check if user is banned
        ban_list = await self.queue_db.get_ban_list()
        if interaction.user.id in ban_list:
            return await interaction.edit_original_response(content=f"{interaction.user.mention}, you have been banned from using this bot feature! ")

        ## check user inputs for things that are too large
        if ddim_steps > 400: ddim_steps = 400
        if n_iter > 10: n_iter = 10

        if samples > 4:
            samples = 4
        ## 1024 crashes the bot anyways, but I'm limiting max render size to 2048
        if width > 2048:
            width = 2048
        ## it won't generate images smaller than 256
        if width < 256:
            width = 256
        if height > 2048:
            height = 2048
        if height < 256:
            height = 256


        ## format the request info  to be sent to the image generator
        ## This sample of request info is the bare minimum that the generator
        ## needs to make an image. If it's another process (such as upscale or variations)
        ## you will need to send more info as seen later
        request_info = {
            'id':round(time.time()),
            'prompt':prompt,
            'requestor':interaction.user.id,
            'done':False,
            'status':'queued',
            'type':'image_gen',
            'ddim_steps':ddim_steps,
            'n_iter':n_iter,
            'seed':seed,
            'height':height,
            'width':width,
            'samples':samples
        }


        ## add the item to the Redis cache queue so that the image generator
        ## server can pick up the item
        await self.queue_db.add_to_queue(request_info)

        ## grab the current queue length to tell the user how long they may have to wait
        queue_length = len(await self.queue_db.get_queue())
        ## motify the user that the request has been added
        await interaction.edit_original_response(content=f'Request approved and added to queue. You are number {queue_length} in queue.\nPrompt: {prompt}')

        ## create an async task to wait for the bot to generate an image
        wait_task = asyncio.create_task(self.wait_for_job(interaction,  request_info), name='waiting_for_job')
        ## wait for the response or the time out, whichevr happens first. 
        ## If there is a timeout, send a cancel signal to the task
        success, no_response = await asyncio.wait([wait_task], return_when=asyncio.FIRST_COMPLETED, timeout=100*queue_length)
        for task in no_response:
            task.cancel()
        for task in success:
            try:
                result = task.result()
                if task.get_name() == "cancelled":
                    user_cancelled = True
                else: user_cancelled = False
            except asyncio.TimeoutError:
                pass
    
    ## this command creates a variant for the image. You can supply the bot with additional arguments
    ## such as a new prompt and strength between 0-1.0
    @app_commands.command(name="ai_variant", description="Generate AI images. Make sure to use NSFW channel for those requests or you could be banned.")
    async def image_variant(self, interaction: discord.Interaction, job_id:int, prompt: str = None, strength: float = None, force_no_prompt:bool=False, ddim_steps: int = 50, n_iter: int = 2, seed:str=None):
        ## check if server is up
        if not await self.check_server_status(interaction): return

        ## If the user didn't input a valid float for the strength then we will default to 70
        if strength is None:
            strength = 0.70
        if strength > 1.0 or strength < 0:
            strength = 0.70
            return await interaction.response.send_message(f"Strength can only be between 0-1.0", ephemeral=True)

        if ddim_steps > 200: ddim_steps = 200
        if n_iter > 10: n_iter = 10
        ## import notes for below:
        ##      -Strength defaults to 0.70
        ##      -Force no prompt default to False, but you can have the bot generate image without prompt
        ##      -Image data is the data on disk from the original job that the variation is based on
        ##      -Version, which is not assigned a value yet is the image that you want to change, it will be presented in the next step
        request_info = {
            'id':None,
            'requestor':interaction.user.id,
            'done':False,
            'status':'queued',
            'type':'variant',
            'prompt' : prompt,
            'version':None,
            'job_id':job_id,
            'strength':strength,
            'force_no_prompt':force_no_prompt,
            'image_data':retrieve_from_disk(job_id),
            'ddim_steps':ddim_steps,
            'n_iter':n_iter,
            'seed':seed
        }

        ## send the user a menu so that they can pick which image they want to make a variation of
        await self.choose_from_source_images(interaction, job_id, request_info, "Which version would you like to make a variant for?", variant_callback, button_name="Variation of")
    
    ## this command creates a variant for the image. You can supply the bot with additional arguments
    ## such as a new prompt and strength between 0-1.0
    @app_commands.command(name="ai_variant_from_web", description="Generate AI images based on a prompt from the web and a source image.")
    async def web_variant(self, interaction: discord.Interaction, url:str, prompt: str, strength: float = None, ddim_steps: int = 50, n_iter: int = 2, seed:str=None):
        ## check if server is up
        if not await self.check_server_status(interaction): return

        ## If the user didn't input a valid float for the strength then we will default to 70
        if strength is None:
            strength = 0.70
        if strength > 1.0 or strength < 0:
            strength = 0.70
            return await interaction.response.send_message(f"Strength can only be between 0-1.0.", ephemeral=True)

        ## verify url
        from urllib.parse import urlparse
        from io import BytesIO
        import requests

        parsed_url = urlparse(url)
        if parsed_url.scheme == '' or parsed_url.netloc == '':
            ## invalid url
            return await interaction.response.send_message(f"The url provided does not match a valid url (make sure it has http/https in the url {url}")
        ## get image and import into pillow
        try:
            response = requests.get(url)
            image = Image.open(BytesIO(response.content))
        except Exception as e:
            return await interaction.response.send_message(f"Received bad URL, unable to parse it into an image.", ephemeral=True)
        
        max_dimension = 512
        if image.height > max_dimension or image.width > max_dimension:
            ratio = image.height/image.width
            if image.height > image.width:
                image = image.resize((round(max_dimension/ratio), max_dimension))
            elif image.width > image.height:
                image = image.resize((max_dimension, round(max_dimension*ratio)))
            else:
                image = image.resize(max_dimension,max_dimension)


        if ddim_steps > 200: ddim_steps = 200
        if n_iter > 10: n_iter = 10
        
        current_time = datetime.datetime.now()
        ## we need to generate the image_data first for easy compatibility
        job_id = round(time.time())
        image_data = {
            'grid_image':image,
            'grid_image_name':None,
            'source_images':[image],
            'source_image_names':['image.jpg'],
            'requestor':interaction.user.id,
            'id':job_id,
            'prompt':prompt,
            'time':current_time,
            'type':'variant',
            'ddim_steps':ddim_steps,
            'n_iter':n_iter,
            'seed':None
        }
        ## store the image data to disk so we can pick it up again
        store_on_disk(image_data)


        ## import notes for below:
        ##      -Strength defaults to 0.70
        ##      -Force no prompt default to False, but you can have the bot generate image without prompt
        ##      -Image data is the data on disk from the original job that the variation is based on
        ##      -Version, which is not assigned a value yet is the image that you want to change, it will be presented in the next step
        request_info = {
            'id':(job_id+1),
            'requestor':interaction.user.id,
            'done':False,
            'status':'queued',
            'type':'variant',
            'prompt' : prompt,
            'version':0,
            'job_id':job_id,
            'strength':strength,
            'force_no_prompt':False,
            'image_data':image_data,
            'seed':seed,
            'ddim_steps':ddim_steps,
            'n_iter':n_iter,
            'seed':None
        }

        ## send the user a menu so that they can pick which image they want to make a variation of
        await self.choose_from_source_images(interaction, job_id, request_info, "Which version would you like to make a variant for?", variant_callback, button_name="Variation of")

    ## this command upscales an image and it can be supplied with the face enhance boolean value
    ## if face enhancement is selected it will run a special AI model that is meant to improve facial features
    @app_commands.command(name="ai_upscale", description="Upscale requests via the job_id. Has additional options such as face enhancement")
    async def image_upscale(self, interaction: discord.Interaction, job_id:int, face_enhance: bool = False):
        ## check if server is up
        if not await self.check_server_status(interaction): return

        ## create request info
        ## import notes for below
        ##      -type is upscale
        ##      -Scale defaults to 4 (4x increase over original 512 --> 2048)
        ##          Note: if you try to upscale an image that's larger than 8000 (2048*4 = 8192 or 8k) it won't allow it due to VRAM
        ##      -Image data is the original image that the upscale will be based on
        ##      -Version, which will be determined later is which of the original images the user wants to scale
        request_info = {
            'id':None,
            'requestor':interaction.user.id,
            'done':False,
            'status':'queued',
            'type':'upscale',
            'prompt' : None,
            'version':None,
            'job_id':job_id,
            'scale':4,
            'face_enhance':face_enhance,
            'image_data':retrieve_from_disk(job_id)
        }
        ## send a menu to the user to ask which version they want to upscale
        await self.choose_from_source_images(interaction, job_id, request_info, "Which version would you like to upscale?", upscale_callback, button_name="Upscale")

    ## this command is like above but allows web requests
    @app_commands.command(name="ai_web_upscale", description="Upscales items from web url.")
    async def web_upscale(self, interaction: discord.Interaction, url:str, face_enhance: bool = False):
        ## check if server is up
        if not await self.check_server_status(interaction): return

        ## verify url
        from urllib.parse import urlparse
        from io import BytesIO
        import requests

        parsed_url = urlparse(url)
        if parsed_url.scheme == '' or parsed_url.netloc == '':
            ## invalid url
            return await interaction.response.send_message(f"The url provided does not match a valid url (make sure it has http/https in the url {url}")
        ## get image and import into pillow
        try:
            response = requests.get(url)
            image = Image.open(BytesIO(response.content))
        except:
            return await interaction.response.send_message(f"Received bad URL, unable to parse it into an image.", ephemeral=True)
        
        max_dimension = 2048
        if image.height > max_dimension or image.width > max_dimension:
            await interaction.response.send_message(f"Warning! this image exceeds {max_dimension} pixels in at least one dimension. It will be resized to {max_dimension} before upscaling", ephemeral=True)
            ratio = image.height/image.width
            if image.height > image.width:
                image = image.resize((round(max_dimension/ratio), max_dimension))
            elif image.width > image.height:
                image = image.resize((max_dimension, round(max_dimension*ratio)))
            else:
                image = image.resize(max_dimension,max_dimension)
            
        current_time = datetime.datetime.now()
        ## we need to generate the image_data first for easy compatibility
        job_id = round(time.time())
        image_data = {
            'grid_image':image,
            'grid_image_name':None,
            'source_images':[image],
            'source_image_names':['image.jpg'],
            'requestor':interaction.user.id,
            'id':job_id,
            'prompt':None,
            'time':current_time,
            'type':'upscale'
        }
        ## store the image data to disk so we can pick it up again
        store_on_disk(image_data)
        ## create request info
        ## import notes for below
        ##      -type is upscale
        ##      -Scale defaults to 4 (4x increase over original 512 --> 2048)
        ##          Note: if you try to upscale an image that's larger than 8000 (2048*4 = 8192 or 8k) it won't allow it due to VRAM
        ##      -Image data is the original image that the upscale will be based on
        ##      -Version, which will be determined later is which of the original images the user wants to scale
        request_info = {
            'id':(job_id+1),
            'requestor':interaction.user.id,
            'done':False,
            'status':'queued',
            'type':'upscale',
            'prompt' : None,
            'version':0,
            'job_id':job_id,
            'scale':4,
            'face_enhance':face_enhance,
            'image_data':image_data
        }
        ## send a menu to the user to ask which version they want to upscale
        await self.choose_from_source_images(interaction, job_id, request_info, "Which version would you like to upscale?", upscale_callback, button_name="Upscale")



    ## this function presents the grid image from a previously generated AI image (from the /ai command)
    ## it needs the info related to the request (request_info) as well
    ## context_text = The question to ask the user (e.g. Which image would you like to upscale?)
    ## callback = function to run when a user clicks on a button
    ## button_name = what the button should be called (e.g. "Variation of X"). This function will insert x as a number
    async def choose_from_source_images(self, interaction: discord.Interaction, job_id, request_info, context_text, callback, button_name = ""):
        ## get job images
        previous_job = retrieve_from_disk(job_id)
        if previous_job is None: return await interaction.response.send_message(f'I could not find the job you specified: {job_id}', ephemeral=True)
        ## it may take more than 3 seconds to get all the items from the job and display them 
        ## so we defer in the interaction
        try:
            await interaction.response.defer(ephemeral=True)
        except:
            pass

        ## if previous job has no source, change source
        ## this happens when the job is an upscale of a previous upscale so there are no variants
        if len(previous_job['source_images']) <= 1:
            ## process immediately
            return await send_request(interaction, request_info, self.bot)
        
        else:

            ## We use the length of items from source images to create menu options
            ## this is handy because it can handle different amount of images to display to the user
            ## for instance, if there are 4 images it will ask which out of the 4, if there are 2 it will display 2, etc
            options = []
            x = 1
            for image in previous_job['source_images']:
                options.append(f"{button_name} {x}".strip())
                x+=1
            ## save the grid image to file and create an attachment for it
            image_path= f"{self.temp_dir}/{previous_job['grid_image_name']}"
            previous_job['grid_image'].save(image_path)
            attachments = []
            attachments.append(discord.File(image_path))
            
            ## start creating the menu so we can display it
            choose_image_menu = InteractionMenu(self.bot)
            ## see below for async callback
            choose_image_menu.custom_button.queue_db = self.queue_db
            choose_image_menu.custom_button.callback = callback
            choose_image_menu.custom_button.request_info = request_info
            choose_image_menu.custom_button.previous_job = previous_job
            ## Generate the menu view with the buttons
            choose_menu_view = await choose_image_menu.generate_view(options, interaction=interaction)

            ## ask user which one they want to up sample
            ## display jobs images
            await interaction.followup.send(context_text, ephemeral=True,files=attachments, view=choose_menu_view)

    ## view the queue for images that are being generated or upscaled
    @app_commands.command(name="ai_queue", description="View the current queue for the AI image generator.")
    async def image_queue(self, interaction: discord.Interaction):

        ## check if server is up
        server_up = await self.check_server_time()
        if server_up is False: return await interaction.response.send_message(f"{interaction.user.mention} the AI image generation server is currently not running. Try again later.", ephemeral=True)

        ## it may take more than 3 seconds to get the queue, so we defer
        await interaction.response.defer(ephemeral=True)
        ## make sure there is somthing in the queue
        image_queue = await self.queue_db.get_queue()
        if len(image_queue)<= 0: queue_embed = discord.Embed(title="Image generator queue",description="Queue is currently empty.")
        else:
            queue_embed = discord.Embed(title="Image generator queue")
            queue_text = ""
            q_number = 1
            ## data comes from Redis unordered so we hve to order it. 
            ## we could sort by date... but instead we aren't right now and just sorting by status
            pending_items = [item for item in image_queue if item['value']['status'] == "pending"]
            non_pending_items = [item for item in image_queue if item not in pending_items]

            ## all of this just generates a bunch of text to display to the user
            sorted_queue = pending_items + non_pending_items
            for key in sorted_queue:
                request = key['value']
                queue_text += f"**{q_number}: "
                if request['type'] == 'image_gen': type="AI image generation"
                queue_text += f"{self.bot.get_user(request['requestor']).name} ** | Task: *{type}* | Status: *{request['status']}*"

                if request['prompt'] is not None:
                    if len(request['prompt']) > 35:
                        prompt= f"{request['prompt'][:18]}...{request['prompt'][-17:]}"
                    else:
                        prompt= request['prompt']
                    ## we only show the actual name of the prompt if the item in the queue is from the person who started the interaction
                    if request['requestor'] == interaction.user.id:
                        queue_text += f"\nPrompt: {prompt}"



                queue_text += "\n"
                q_number += 1
            
            queue_embed.add_field(name="Queue List", value=queue_text)

        ## send the queue
        await interaction.edit_original_response(embed=queue_embed)
    
    ## show your latest 25 requests from the bot
    ## the reason that it's limited to 25 is because discord doesn't allow embeds that have more than 25 fields
    ## at some point in the future a better system should be made to handle n amount of user requests. This is not the world we live in.
    @app_commands.command(name="ai_my_requests", description="View your old requests.")
    async def my_requests(self, interaction: discord.Interaction, more:bool=False):
        await interaction.response.defer(ephemeral=True)
        user_requests = await self.queue_db.get_user_requests(interaction.user.id)
        if user_requests is None: return await interaction.response.send_message(f"{interaction.user.mention}, you don't have any requests", ephemeral=True)
        if len(user_requests) <= 0: return await interaction.response.send_message(f"{interaction.user.mention}, you don't have any requests", ephemeral=True)
        ## sort requests latest to oldest
        user_requests.sort(key = lambda x:x['time'], reverse=True)

        if more is False:
            user_requests_embed = discord.Embed(title="Last 25 requests", description="User `/ai_view_request [job id]` to see an old request.")
            x = 0
            ## generate all the text
            for request in user_requests:
                if x >24: break
                if len(request['prompt']) > 40:
                    ## truncate prompts because they can get too long
                    prompt= f"{request['prompt'][:18]}...{request['prompt'][-17:]}"
                else:
                    prompt= request['prompt']
                if 'seed' in request:
                    seed = request['seed']
                else:
                    seed = "N/A"
                user_requests_embed.add_field(name=f"{x+1}: {prompt}", value=f"Job ID: {request['id']}\nTime: {request['time'].strftime('%I:%M %p %m-%d-%y')}\nType: {request['type']}\nSeed: {seed}", inline=False)

                x += 1
            return await interaction.edit_original_response(embed=user_requests_embed)
        else:
            user_history = f"plugins/ai_image_generator/_tmp/{interaction.user.id}_history.txt"
            x=0
            with open(user_history, 'w') as file:
                for request in user_requests:
                    try:
                        if isinstance(request, str): continue
                        if not 'id' in request: continue
                        if not 'time' in request: continue
                        if not 'type' in request: continue
                        
                        ## prompt
                        prompt = request['prompt'] if 'prompt' in request else "N/A"
                        ## seed
                        seed = request['seed'] if 'seed' in request else "N/A"
                        ## n_iter
                        n_iter = request['n_iter'] if 'n_iter' in request else "N/A"
                        ## ddim_steps
                        ddim_steps = request['ddim_steps'] if 'ddim_steps' in request else "N/A"
                        ## parent
                        parent = request['parent'] if 'parent' in request else "N/A"

                        try:
                            request_str = f"{x+1}: {prompt}\nJob ID: {request['id']}\nTime: {request['time'].strftime('%I:%M %p %m-%d-%y')}\nType: {request['type']}\nSeed: {seed}\nParent Job: {parent}\nDDIM Steps: {ddim_steps}\nn_iter (generations): {n_iter}\n\n"
                            file.write(request_str)
                        except:
                            file.write(f"Failed to display request {x+1}\n\n")
                            
                        
                    except:
                        file.write(f"Failed to display request {x+1}\n\n")
                    x+=1

            await interaction.edit_original_response(attachments=[discord.File(user_history)], content=f"Here is your complete user history.")
            os.remove(user_history)


    ## clear your personal history. This only deletes your own history
    ## there's no safety, but maybe there should be. 
    @app_commands.command(name="ai_clear_history", description="Clear out your history.")
    async def clear_history(self, interaction: discord.Interaction):
        ## check if user is banned
        ## if a user is banned we may want to see their prompts as justification for the ban
        ban_list = await self.queue_db.get_ban_list()
        if interaction.user.id in ban_list:
            return await interaction.response.send_message(f"{interaction.user.mention}, you have been banned from using this bot feature! ",ephemeral=True)

        user_requests = await self.queue_db.get_user_requests(interaction.user.id)
        if user_requests is None: return await interaction.response.send_message(f"{interaction.user.mention}, you don't have any requests", ephemeral=True)
        if len(user_requests) <= 0: return await interaction.response.send_message(f"{interaction.user.mention}, you don't have any requests", ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        await self.queue_db.delete_user_history(interaction.user.id)

        await interaction.edit_original_response(content=f"{interaction.user.mention}, your history has been deleted. I wonder what you were up to...")

    ## view a request and display the menu to give options for editing the request
    @app_commands.command(name="ai_view_request", description="View a specific past job.")
    async def view_request(self, interaction: discord.Interaction, job_id:int, public:bool=False):
        if public is True: ephemeral=False
        else: ephemeral=True
        await interaction.response.defer(ephemeral=ephemeral)
        await self.image_control_menu(interaction, job_id, ephemeral=ephemeral)

    ## ban a user from using the generator, requires highest priviledges
    @app_commands.command(name="ai_ban_user", description="Bans a user from using the AI image generator.")
    #@app_commands.checks.has_any_role(settings.discord.perms.superadminrole, settings.discord.perms.sudorole)
    async def ban_user(self, interaction: discord.Interaction, user: discord.User):
        if not auth.check_role(settings, interaction.guild, interaction.user, ['superadmin', 'sudo']): return await auth.not_auth_message(interaction=interaction)

        await self.queue_db.add_to_ban_list(user.id)
        await interaction.response.send_message(f"{user.mention}, you have been banned from using the AI image generator!")
    ## unban a user from using the generator, requires highest priviledges
    #@app_commands.command(name="ai_unban_user", description="Unbans a user from the AI image generator.")
    #@app_commands.checks.has_any_role(settings.discord.perms.superadminrole, settings.discord.perms.sudorole)
    async def unban_user(self, interaction: discord.Interaction, user: discord.User):
        if not auth.check_role(settings, interaction.guild, interaction.user, ['superadmin', 'sudo']): return await auth.not_auth_message(interaction=interaction)

        await self.queue_db.remove_from_ban_list(user.id)
        await interaction.response.send_message(f"{user.mention}, your ban on using the AI image generator has been lifted!")
    
    ## clears out the queue if it gets bungled with stuff
    ## soft will try and clear items that are not currently running and not marked as "done"
    ## hard reset will 'cancel' running jobs too (cancel means they won't display, but if the AI gen server has picked it up already it will finish)
    @app_commands.command(name="ai_clear_queue", description="Clear the current queue. Soft clear deletings queued jobs. Hard clear deletes all jobs.")
    @app_commands.choices(action=[
        discord.app_commands.Choice(name='soft', value="soft"),
        discord.app_commands.Choice(name='hard', value="hard")
    ]) 
    #@app_commands.checks.has_any_role(settings.discord.perms.superadminrole, settings.discord.perms.sudorole)
    async def clear_queue(self, interaction: discord.Interaction, action: discord.app_commands.Choice[str]):
        if not auth.check_role(settings, interaction.guild, interaction.user, ['superadmin', 'sudo']): return await auth.not_auth_message(interaction=interaction)

        await interaction.response.send_message("Deleting queue...", ephemeral=True)

        if action.value == 'hard':
            await self.queue_db.delete_queue()
            return await interaction.edit_original_response(content="Deleted queue including running and finished jobs.")
        
        if action.value == 'soft':
            image_queue = await self.queue_db.get_queue()
            if len(image_queue) <= 0: return interaction.edit_original_response(content="Queue is already empty.")

            
            for key in image_queue:
                request = key['value']
                if request['status'] == "queued":
                    await self.queue_db.delete_request(request['id'])

            #await self.queue_db.delete_queue()
            await interaction.edit_original_response(content="Deleted queue. Running jobs will still continue.")

    ## destroy everything from the database and local files
    ## this will completely reset the AI image gen server back to default and everyone will lose their requests
    ## requires highest priviledges to run
    @app_commands.command(name="ai_purge", description="Removes all stored jobs and files.")
    #@app_commands.checks.has_any_role(settings.discord.perms.superadminrole, settings.discord.perms.sudorole)
    async def purge_storage(self, interaction: discord.Interaction):
        if not auth.check_role(settings, interaction.guild, interaction.user, ['superadmin', 'sudo']): return await auth.not_auth_message(interaction=interaction)

        await interaction.response.send_message("Purging all contents...", ephemeral=True)


        await self.queue_db.delete_queue()
        await interaction.edit_original_response(content="Deleted queue including running and finished jobs.")


        ## delete old requests stored under server.ai_image.completed.index
        await interaction.edit_original_response(content="Deleting old image requests and user requests")
        await self.queue_db.delete_all_requests()
        
        await interaction.edit_original_response(content="Deleting local files")
        ## delete local files
        dirs = ["plugins/ai_image_generator/_tmp","plugins/ai_image_generator/output_images","plugins/ai_image_generator/storage"]
        for dir in dirs:
            for f in os.listdir(dir):
                os.remove(os.path.join(dir, f))
        
        await interaction.edit_original_response(content="Purge complete!")

    ## this is a generic menu for displaying images as well as a few control options for the images, such as making variations, upscales, or downloading a single image
    ## notes:
    ##      -ephemeral will make the image not display, this is useful when a user wants to view a request
    ##          By default it's turned off because we want to display requests to everyone
    ##      -Webhook message is a variable that can edit a previous response instead of using the mainline interaction
    ##      -First is to display different title text when an image is first made (e.g. proudly presented by...)
    async def image_control_menu(self, interaction: discord.Interaction, job_id, ephemeral=False, webhook_message = None, first=False):
        ## load image from database
        #completed_data = await self.queue_db.get_image(job_id, interaction.user.id)
        data = retrieve_from_disk(job_id)
        if data is None: 
            completed_data = await self.queue_db.get_image(job_id, interaction.user.id)
            if completed_data is None: found = False
            else:
                ## check for completed jobs instead
                found = True
                data = pickle.loads(completed_data)
                ## move to disk
                store_on_disk(data)
                ## remove data
                await self.queue_db.delete_completed_request(data['id'])
            if found is False:
                return await interaction.followup.send(f"I couldn't find job {job_id}",ephemeral=True)

        image_path = f"plugins/ai_image_generator/output_images/{data['id']}.jpg"
        ## save grid image to file
        data['grid_image'].save(image_path)

        # Display image
        if webhook_message is None:
            await interaction.edit_original_response(content="Finished processing image")
        else:
            await webhook_message.edit(content="Finished processing image")
        if data['prompt'] is None: data['prompt'] = ""



        if len(data['source_images']) > 0:
            image_control_menu_view = ImageControls.generate_view(self.bot, self, data)
        else: 
            image_control_menu_view = ImageControls.generate_view(self.bot, self, data, upscale=True, variation=True, enhance_face=True, download=False)

        if first is True:
            title_str = f"Proudly presented by {interaction.user.name}"
        else:
            title_str = f"Original prompt by {self.bot.get_user(data['requestor']).name}"

        ## check if server is up
        if not await self.check_server_status(interaction, quiet=True): image_control_menu_view = None

        # if 'seed' in data:
        #     seed = data['seed']
        # else:
        #     seed = "N/A"
        
        ## setup embed
        ## add title and description
        if 'server_message' in data:
            image_control_embed = discord.Embed(title=title_str, description=data['server_message'])
        else:
            image_control_embed = discord.Embed(title=title_str)

        ## add run details
        image_control_embed.add_field(name="Details", value=f"Prompt:\n*{str(data['prompt'])}*\nJob ID: {data['id']}")

        if image_control_menu_view is not None:
            await interaction.followup.send(embed=image_control_embed, file=discord.File(image_path), view=image_control_menu_view, ephemeral=ephemeral)
        else:
            await interaction.followup.send(embed=image_control_embed, file=discord.File(image_path), ephemeral=ephemeral)
        

    ## this is the function that waits for job completion asyncronously by checking the queue every 5 seconds
    async def wait_for_job(self, interaction:discord.Interaction, request, followup_webhook=None):
        try:
            last_status = None
            while True:
                ## get the specific item in the queue
                user_request = await self.queue_db.retrieve_request(request['id'])
                if user_request is None: break
                if last_status == user_request['status']:
                    pass
                else:
                    ## if the status is pending then notify the user the AI server has picked up their image and will process it shortly
                    if user_request['status'] == "pending":
                        last_status = "pending"
                        if followup_webhook is None:
                            await interaction.edit_original_response(content=f"Request picked up by the magic image leprechaun ☘️!\nPrompt: {request['prompt']}")
                        else:
                            await followup_webhook.edit(content=f"Request picked up by the magic image leprechaun ☘️!\nPrompt: {request['prompt']}")
                    ## if item is done process...
                    if user_request['done'] is True:
                        ## delete item from queue
                        await self.queue_db.delete_request(user_request['id'])
                        print(f"Request {user_request['id']} deleted from queue because finished!")

                        # retrieve completed data
                        ## this is the only time all the image data is in the Redis Cache
                        ## the image data is too large to store there permanently so we will retrieve it, store to disk, then delete it
                        completed_data = await self.queue_db.get_image(user_request['id'], interaction.user.id)
                        data = pickle.loads(completed_data)
                        ## save request to disk
                        store_on_disk(data)

                        ## remove request from Redis to save on memory
                        await self.queue_db.delete_completed_request(user_request['id'])
                        ## display the image with further controls
                        await self.image_control_menu(interaction, user_request['id'], webhook_message=followup_webhook, first=True)
                ## notify the user of failures and give them the job ID because discord bot may have failed and not the AI server
                if user_request['status'] == "failed":
                    if followup_webhook is None:
                        await interaction.edit_original_response(content=f"Sorry, I was unable to fulfill your request. I'm still working on your request and you can check the status with `ai_view_request job_id:{user_request['id']}`")
                    else:
                        #await interaction.followup.edit_message()
                        await followup_webhook.edit(content=f"Sorry, I was unable to fulfill your request. I'm still working on your request and you can check the status with `ai_view_request job_id:{user_request['id']}`. If this is a variant from a web image, some images just don't work.")
                    await self.queue_db.delete_request(user_request['id'])
                    break

                ## wait 5 seconds before trying again
                await asyncio.sleep(5)
        except asyncio.CancelledError:
            await interaction.followup.send(f"{interaction.user.mention} Sorry, I was unable to process your request in a reasonable time.  I am probably still working on your request and you can check the status with `ai_view_request job_id:{user_request['id']}`")            
    ## function to check if an image is too big
    def check_upscale_size(self, image):
        w, h = image.size
        if w > self.max_upscale_width or h > self.max_upscale_height:
            return False
        else: return True
    def check_variant_size(self, image):
        w, h = image.size
        if w > self.max_variant_width or h > self.max_variant_height:
            return False
        else: return True
    def resize_with_aspect_ratio(self, image, w=512,h=512):
        ratio = image.height/image.width
        if image.height > image.width:
            image = image.resize((round(w/ratio), h))
        elif image.width > image.height:
            image = image.resize((w, round(h*ratio)))
        else:
            image = image.resize((w,h))
        return image

    ## get the status of the server by checking the last time it pinged
    async def check_server_status(self, interaction: discord.Interaction, quiet=False, prompt = None):
            ## check if server is up
        server_up = await self.check_server_time()
        if server_up is False: 
            if quiet is False:
                if prompt is None:
                    message = f"{interaction.user.mention} the AI image generation server is currently not running. Try again later."
                else:
                    message = f"{interaction.user.mention} the AI image generation server is currently not running. Try again later.\n Prompt: {prompt}"
                await interaction.edit_original_response(content=message)
            return False
        else: return True
    ## the AI server 
    async def check_server_time(self):
        latest_server_ping = await self.queue_db.get_generator_server_ping()
        if latest_server_ping is not None:
            latest_server_ping = parser.parse(latest_server_ping)
            if (latest_server_ping + datetime.timedelta(seconds=60)) < datetime.datetime.now(): return False
            else: return True
        else:
            return False

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AI_image_gen_cog(bot))

async def image_selection_callback(self, interaction: discord.Interaction) -> None:
    image_path = f"plugins/ai_image_generator/_tmp/{self.previous_job['id']}_{self.index}.jpg"
    self.previous_job['source_images'][self.index].save(image_path)

    return await interaction.response.send_message(f"Image download", file=discord.File(image_path), ephemeral=True)
    
## button call back for when a user clicks on a button to create a variant from choose_image menu
async def variant_callback(self, interaction: discord.Interaction) -> None:
    ## if they choose cancel
    if self.value.lower() == "cancel":
        return await self.menu_message.edit_original_response(content=f"Cancelled menu.", view=None, embed=None)
    self.request_info['id'] = None
    self.request_info['version'] = self.index
    await send_request(interaction, self.request_info, self.bot)

## button call back for when a user clicks on a button to create a variant from choose_image menu
async def upscale_callback(self, interaction: discord.Interaction) -> None:
    if self.value.lower() == "cancel":
        return await self.menu_message.edit_original_response(content=f"Cancelled menu.", view=None, embed=None)
    self.request_info['id'] = None
    self.request_info['version'] = self.index
    await send_request(interaction, self.request_info, self.bot)

## generic function for sending a request (that is not an initial AI image generation request from /ai command) to the AI server
## requires the request_info and the bot object because we need to instantiate the cog to get some of the functions from it such as:
##      -check_upscale_size
##      -queue_db
##      -add_to_queue
## notifies the user the item has been sent to the queue
async def send_request(interaction: discord.Interaction, request_info, bot):
    try:
        await interaction.response.defer(ephemeral=True)
    except:
        pass
    
    if request_info['id'] is None:
        request_info['id'] = round(time.time())

    image_gen = AI_image_gen_cog(bot)

    if len(request_info['image_data']['source_images']) > 0:
        image = request_info['image_data']['source_images'][request_info['version']]
    else:
        image = request_info['image_data']['grid_image']

    if not image_gen.check_upscale_size(image): return await interaction.followup.send(f"{interaction.user.mention}, the image you requested is too large. It exceeds {image_gen.max_upscale_height} x {image_gen.max_upscale_width} pixels", ephemeral=True)

    ## resize image for variant
    if request_info['type'] == 'variant':
        ## if there are no source images, use the grid image
        if len(request_info['image_data']['source_images']) > 0:

            if not image_gen.check_variant_size(request_info['image_data']['source_images'][request_info['version']]):
                ## resize to self.max_variant_width and self.max_variant_height
                print(f"Need to resize variant for request {request_info['id']} with source image")
                request_info['image_data']['source_images'][request_info['version']] = image_gen.resize_with_aspect_ratio(request_info['image_data']['source_images'][request_info['version']], w=image_gen.max_variant_width, h=image_gen.max_variant_height)
        else:
            if not image_gen.check_variant_size(request_info['image_data']['grid_image']):
                request_info['image_data']['grid_image'] = image_gen.resize_with_aspect_ratio(request_info['image_data']['grid_image'])
                print(f"Need to resize variant for request {request_info['id']} with grid image")


    await image_gen.queue_db.add_to_queue(request_info)
    queue_length = len(await image_gen.queue_db.get_queue())


    followup_webhook = await interaction.followup.send(content=f'Request approved and added to queue. You are number {queue_length} in queue.',ephemeral=True)

    ## this is similar to the section where we create a task for `/ai` command
    wait_task = asyncio.create_task(image_gen.wait_for_job(interaction, request_info, followup_webhook = followup_webhook), name='waiting_for_job')

    success, no_response = await asyncio.wait([wait_task], return_when=asyncio.FIRST_COMPLETED, timeout=100*queue_length)
    for task in no_response:
        task.cancel()
    for task in success:
        try:
            result = task.result()
            if task.get_name() == "cancelled":
                user_cancelled = True
            else: user_cancelled = False
        except asyncio.TimeoutError:
            pass

## This is the class for creating the ImageControl menu with all of it's buttons
class ImageControls:
    def generate_view(bot, image_gen, request, upscale=True, variation=True, enhance_face=False, download=True):
        controls_view = ImageControls.controls_view(bot, image_gen, request)
        ## we run this section to change some of the buttons to disabled or enabled depending on how you start this class
        if upscale is False:
            controls_view.children[0].disabled= True
        if variation is False:
            controls_view.children[1].disabled= True
        if enhance_face is True:
            controls_view.children[2].disabled= False
        if download is False:
            controls_view.children[3].disabled= True
        return controls_view

            
    class controls_view(discord.ui.View):
        def __init__(self, bot, image_gen, request):
            super().__init__()
            self.bot = bot
            self.image_gen = image_gen
            self.request = request
        ## default request info for an upscale
        @discord.ui.button(label='Upscale', style=discord.ButtonStyle.grey, row=0)
        async def upscale(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.edit_message(view=self)
            request_info = {
                'id':None,
                'requestor':interaction.user.id,
                'done':False,
                'status':'queued',
                'type':'upscale',
                'prompt' : None,
                'version':None,
                'job_id':self.request['id'],
                'scale':4,
                'face_enhance':False,
                'image_data':retrieve_from_disk(self.request['id']),
                'ddim_steps':50,
                'n_iter':2,
                'seed':None
            } 
            return await self.image_gen.choose_from_source_images(interaction, self.request['id'], request_info, "Choose an image to upscale", upscale_callback, button_name="Upscale")
    
        ## default request info for a variation
        @discord.ui.button(label='Make variation', style=discord.ButtonStyle.grey, row=0)
        async def variant(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.edit_message(view=self)
            request_info = {
                'id':None,
                'requestor':interaction.user.id,
                'done':False,
                'status':'queued',
                'type':'variant',
                'prompt' : self.request['prompt'],
                'version':None,
                'job_id':self.request['id'],
                'strength':0.70,
                'force_no_prompt':False,
                'image_data':retrieve_from_disk(self.request['id']),
                'ddim_steps':50,
                'n_iter':2,
                'seed':None
            }

            return await self.image_gen.choose_from_source_images(interaction, self.request['id'], request_info, "Choose an image to make variations", variant_callback, button_name="Make variant of")


        ## default info a face enhancement
        @discord.ui.button(label='Enhance Face', style=discord.ButtonStyle.grey, row=0, disabled=True)
        async def upscale_face(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.edit_message(view=self)
            request_info = {
                'id':None,
                'requestor':interaction.user.id,
                'done':False,
                'status':'queued',
                'type':'upscale',
                'prompt' : None,
                'version':None,
                'job_id':self.request['id'],
                'scale':1,
                'face_enhance':True,
                'image_data':retrieve_from_disk(self.request['id']),
                'ddim_steps':50,
                'n_iter':2,
                'seed':None
            } 
            return await self.image_gen.choose_from_source_images(interaction, self.request['id'], request_info, "Choose an image to upscale", upscale_callback, button_name="Enhance face for")
    

        ## allow user to download image
        @discord.ui.button(label='Download Image', style=discord.ButtonStyle.grey, row=0)
        async def download(self, interaction: discord.Interaction, button: discord.ui.Button):
            ## respond to interaction with nothing...
            await interaction.response.edit_message(view=self)
            return await self.image_gen.choose_from_source_images(interaction, self.request['id'], None, "Which image would you like?", image_selection_callback)

        ## allow user to download image
        @discord.ui.button(label='More info', style=discord.ButtonStyle.grey, row=0)
        async def more_info(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.edit_message(view=self)
            additional_info = discord.Embed(title=f"Additional info for job {self.request['id']}")
            ## seed
            seed = self.request['seed'] if 'seed' in self.request else "N/A"
            ## n_iter
            n_iter = self.request['n_iter'] if 'n_iter' in self.request else "N/A"
            ## ddim_steps
            ddim_steps = self.request['ddim_steps'] if 'ddim_steps' in self.request else "N/A"

            info_str = f"Seed: {seed}\ngenerations (n_iter): {n_iter}\nDDIM Steps: {ddim_steps}"

            if 'parent' in self.request:
                if self.request['parent'] is not None:
                    info_str += f"\nParent job: {self.request['parent']}"

            additional_info.add_field(name="\u200b", value=info_str)
            return await interaction.followup.send(embed=additional_info, ephemeral=True)

        ## cancel menu and remove it
        @discord.ui.button(label='Cancel', style=discord.ButtonStyle.red, row=1)
        async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
            ## respond to interaction with nothing...
            await interaction.response.edit_message(view=None)
            return

## pickles the complete image data as binary 
## contains this data:
# post_processing_data_full = {
#     'grid_image':gen_image,
#     'grid_image_name':grid_file[0],
#     'source_images':source_images,
#     'source_image_names':source_files,
#     'requestor':request['requestor'],
#     'id':request['id'],
#     'prompt':request['prompt'],
#     'time':current_time,
#     'type':request['type']
# }
def store_on_disk(complete_image_data):
    with open(f"plugins/ai_image_generator/storage/{complete_image_data['id']}", "wb") as f:
        pickle.dump(complete_image_data, f)
## reverse of above. see previous for data retrieved
def retrieve_from_disk(request_id):
    try:
        with open(f"plugins/ai_image_generator/storage/{request_id}", "rb") as f:
            data = pickle.load(f)
    except (FileNotFoundError, EOFError):
        data = None
    return data

