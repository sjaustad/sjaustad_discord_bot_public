import asyncio, pickle, os, random
from logging import exception
from distutils.command.clean import clean
from http.client import REQUEST_HEADER_FIELDS_TOO_LARGE
from locale import currency
import re
from PIL import Image
from subprocess import Popen, STDOUT, DEVNULL
import datetime, sys
Image.MAX_IMAGE_PIXELS = 999999999

from database.redis_connector import Async_Redis
redis = Async_Redis()

from server_message import message


async def main():
    await redis.create_pool()

    if not os.path.exists("output"):
        os.mkdir("output")
    if not os.path.exists("Real-ESRGAN/input"):
        os.mkdir("Real-ESRGAN/input")
    if not os.path.exists("Real-ESRGAN/input/upscales"):
        os.mkdir("Real-ESRGAN/input/upscales")
    if not os.path.exists("output/variants"):
        os.mkdir("output/variants")

    from database.calls.queue import Queue
    queue_db = Queue(redis)


    ## clear out queue on start
    await queue_db.delete_queue()

    while True:

        current_queue = None

        while current_queue is None:
            try:
                ## publish alive
                await queue_db.publish_time()
                current_queue = await queue_db.get_queue()
                break
            except Exception as e:
                print("Failed to get publish time or get queue from database. Retrying in 10 seconds...")
                await asyncio.sleep(10)
                print("Retrying...")

        if current_queue is None: current_queue = []

        if len(current_queue) <= 0:
            print("Nothing in the queue!")

        for item in current_queue:
            try:
                ## publish alive
                await queue_db.publish_time()
            except:
                pass
            
            request = item['value']

            ## if item is listed as done skip
            if request['done'] is True:
                print("item marked as done, skipping...")
                try:
                    await queue_db.delete_request(request['id'])
                except:
                    print(f"Failed to delete finished request {request['id']} from queue")
                    continue
                continue

            elif request['status'] == 'pending':
                print("item marked as pending, skipping...")
                continue


            print(f"New request received from user {request['requestor']}\nProcessing item: {request['id']}")

            max_retries = 0
            while max_retries < 3:
                try:
                    await queue_db.update_status(request, "pending")
                    break
                except Exception as e:
                    print(f"Failed to publish status for request {request['id']}. Retrying in 10 seconds")
                    await asyncio.sleep(10)
                    max_retries += 1
                    print("Retrying...")
            if max_retries >= 3:
                print(f"Failed to publish status for job after {max_retries} attempts. Skipping request {request['id']}...")
                continue


                


            ## check type:
            if request['type'] == "image_gen":
                print(f"Beginning new image generation for request {request['id']}")

                ## begin processing

                request['prompt'] = clean_string(request['prompt'])
                #generator_process = Popen(f"python sd2/home/austax/stable-diffusion/stable-diffusion/scripts/txt2img.py --prompt '{request['prompt']}' --plms --ckpt /home/austax/stable-diffusion/stable-diffusion/sd-v1-4.ckpt --n_samples 2 --file_prefix {request['id']} --outdir /home/austax/stable-diffusion/stable-diffusion/output --seed {str(random.randint(1,99999999))} --n_rows 2", shell=True)
                #exit_code = generator_process.wait()
                #print(f"EXIT CODE: {exit_code}")

                ## get seed
                if request['seed'] is None:
                    seed = str(random.randint(1,99999999))
                else:
                    seed = str(request['seed'])
                
                if request['height'] is None:
                    height = 512#int(request['height'])
                else:
                    height = int(request['height'])
                if request['width'] is None:
                    width = 512
                else:
                    width = int(request['width'])
                
                ## default to 4x4 grid
                if request['samples'] is None:
                    samples = 2
                else:
                    samples = int(request['samples'])

                status = start_process(f"python scripts/txt2img.py --prompt '{request['prompt']}' --plms --ddim_steps {request['ddim_steps']} --n_iter {request['n_iter']} --ckpt sd-v1-4.ckpt --n_samples {samples} --file_prefix {request['id']} --outdir output --seed {seed} --n_rows {samples} --H {height} --W {width}")
                ## if can't generate, update status
                if status is False:
                    try:
                        await queue_db.update_status(request, "failed")
                        continue
                    except:
                        print(f"Unable to delete failed request: {request['id']}")
                        continue


                grid_file = [filename for filename in os.listdir("output") if filename.startswith(str(request['id']))]
                file = f"output/{grid_file[0]}"

            elif request['type'] == "variant":
                if 'job_id' not in request:
                    ## no job id provided for upscaling
                    print(f"Could not process {request['id']} because job is missing.")
                    try:
                        await queue_db.delete_request(request['id'])
                    except:
                        print(f"Failed to delete {request['id']} from queue")
                if 'version' not in request:
                    ## no version, default to first
                    print(f"No version given for {request['id']} defaulting to version 0")
                    request['version'] = 0


                if request['strength'] is None:
                    request['strength'] = 0.5
                print(f"Creating variant for request {request['id']}")



                original_job_data = request['image_data']

                if original_job_data is None:
                    ## if you can't find it delete the new job
                    print(f"Could not process {request['id']} because job {request['job_id']} could not be found in database.")
                    try:
                        await queue_db.delete_request(request['id'])
                    except:
                        print(f"Failed to delete {request['id']} from queue.")
                        continue
                    continue

                ## save the origal image to disk
                image_path = f"output/variants/{request['job_id']}.jpg"
                if len(original_job_data['source_images']) > 0:
                    original_job_data['source_images'][request['version']].save(image_path)
                else:
                    original_job_data['grid_image'].save(image_path)

                original_job_data['prompt'].replace("Upscale of","").strip()
                original_job_data['prompt'].replace("Variation of","").strip()


                ## get seed
                if request['seed'] is None:
                    seed = str(random.randint(1,99999999))
                else:
                    seed = str(request['seed'])

                if request['force_no_prompt'] is False:
                    
                    ## setup the process img2img
                    if request['prompt'] is None:
                        process_string = f"python scripts/img2img.py --prompt '{original_job_data['prompt']}' --init-img {image_path} --ckpt sd-v1-4.ckpt --ddim_steps {request['ddim_steps']} --n_iter {request['n_iter']} --n_samples 2 --n_rows 2 --file_prefix {request['id']} --outdir output/ --seed {seed} --strength {request['strength']}"
                    else:
                        process_string = f"python scripts/img2img.py --prompt '{request['prompt']}' --init-img {image_path} --ckpt sd-v1-4.ckpt --ddim_steps {request['ddim_steps']} --n_iter {request['n_iter']} --n_samples 2 --n_rows 2 --file_prefix {request['id']} --outdir output/ --seed {seed} --strength {request['strength']}"
                else:
                    process_string = f"python scripts/img2img.py  --init-img {image_path} --ckpt sd-v1-4.ckpt --ddim_steps {request['ddim_steps']} --n_iter {request['n_iter']} --n_samples 2 --n_rows 2 --file_prefix {request['id']} --outdir output/ --seed {seed} --strength {request['strength']}"


                status = start_process(process_string)
                ## if can't generate, update status
                if status is False:
                    try:
                        await queue_db.update_status(request, "failed")
                        continue
                    except:
                        print(f"Unable to delete failed request: {request['id']}")
                        continue

                request['prompt'] = original_job_data['prompt']


                grid_file = [filename for filename in os.listdir("output") if filename.startswith(str(request['id']))]
                file = f"output/{grid_file[0]}"
            
            elif request['type'] == "upscale":
                seed=None
                if 'job_id' not in request:
                    ## no job id provided for upscaling
                    print(f"Could not process {request['id']} because job is missing.")
                    try:
                        await queue_db.delete_request(request['id'])
                    except:
                        print(f"Couldn't delete {request['id']} from queue. Skipping...")
                        continue
                if 'version' not in request:
                    ## no version, default to first
                    print(f"No version given for {request['id']} defaulting to version 0")
                    request['version'] = 0


                if request['scale'] is None:
                    request['scale'] = 4
                print(f"Running upscale for request {request['id']}")

                original_job_data = request['image_data']


                if original_job_data is None:
                    ## if you can't find it delete the new job
                    print(f"Could not process {request['id']} because job {request['job_id']} could not be found in database.")
                    try:
                        await queue_db.delete_request(request['id'])
                    except:
                        print(f"Couldn't delete {request['id']} from queue. Skipping...")
                        continue
                    continue

                ## save the origal image to disk
                os.chdir('Real-ESRGAN/')
                input_file = f"input/upscales/{request['job_id']}.jpg"

                if len(original_job_data['source_images']) > 0:
                    pil_image = original_job_data['source_images'][request['version']]
                else:
                    pil_image = original_job_data['grid_image']
                
                ## stop scaling the image if it's too big
                width, height = pil_image.size
                if width <= 8000:
                    pil_image.save(input_file)

                    print(f"SCALE: {request['scale']}")
                    if request['face_enhance'] is False:
                        process_string = f"python inference_realesrgan.py -i {input_file} -s {request['scale']} -t 512"
                    else:
                        print(f"Running upscale for {request['id']} with face enhancement.")
                        process_string = f"python inference_realesrgan.py -i {input_file} --face_enhance -s {request['scale']} -t 512"
                    
                    status = start_process(process_string)
                    
                    try:
                        os.rename(f"results/{original_job_data['id']}_out.jpg",f"results/{str(request['id'])}.jpg")
                    except FileNotFoundError:
                        status = False
                else: 
                    status = False
                
                ## if can't generate, update status
                if status is False:
                    try:
                        print(f"{request['id']} failed to upscale image")
                        await queue_db.update_status(request, "failed")
                        os.chdir('../')
                        continue
                    except:
                        print(f"Unable to delete failed request: {request['id']}")
                        os.chdir('../')
                        continue


                request['prompt'] = original_job_data['prompt']
                

                
                grid_file = [filename for filename in os.listdir("results") if filename.startswith(str(request['id']))]

                os.chdir('../')
                file = f"Real-ESRGAN/results/{grid_file[0]}"

            else: continue

            ## get the source files:
            source_files = [filename for filename in os.listdir("output/samples") if filename.startswith(str(request['id']))]
            source_files.sort()
            ## load image
            try:
                gen_image = Image.open(file)
            except:
                print("Failed to open final image with PIL. This could be due to a decompression bomb warning.")
                await queue_db.update_status(request, 'failed')
                continue

            source_images = []
            for im in source_files:
                source_images.append(Image.open(f"output/samples/{im}"))
            current_time = datetime.datetime.now()
            post_processing_data_simple = {
                'grid_image_name':grid_file[0],
                'source_image_names':source_files,
                'requestor':request['requestor'],
                'id':request['id'],
                'prompt':request['prompt'],
                'time':current_time,
                'type':request['type'],
                'seed':seed,
                'server_message':f"This render was provided by {message.owner} using a {message.GPU}."
            }
            post_processing_data_full = {
                'grid_image':gen_image,
                'grid_image_name':grid_file[0],
                'source_images':source_images,
                'source_image_names':source_files,
                'requestor':request['requestor'],
                'id':request['id'],
                'prompt':request['prompt'],
                'time':current_time,
                'type':request['type'],
                'seed':seed,
                'server_message':f"This render was provided by {message.owner} using a {message.GPU}."
            }

            max_retries = 0
            while max_retries < 3:
                try:
                    await queue_db.store_data_simple(request['id'], post_processing_data_simple)
                    await queue_db.store_data_full(request['id'], post_processing_data_full)

                    await queue_db.mark_finished(request)
                    await queue_db.update_status(request, "done")
                    print(f"Finished processing request {request['id']} and uploaded to database")
                    break
                except Exception as e:
                    print(f"Failed to store request {request['id']}. Retrying in 5 seconds\n{e}")
                    await asyncio.sleep(5)
                    max_retries += 1
                    print("Retrying...")
            if max_retries >= 3:
                print(f"Failed to store content for request {request['id']}. Moving on to next job...")
                continue





        await asyncio.sleep(10)

def clean_string(string):
    illegal_chars = "!@#$%^&*()'[]\{\}`~|<>;\""

    for char in illegal_chars:
        string = string.replace(f"{char}", "")
    return string


def start_process(process_string, max_retries = 2):
    attempts = 1
    success = False
    while attempts <= max_retries:
        try:
            generator_process = Popen(process_string, shell=True, stdout=DEVNULL, stderr=STDOUT)
            exit_code = generator_process.wait()
            if exit_code != 0:
                attempts += 1
            else:
                success=True
                break
        except:
            attempts+=1

    return success

asyncio.run(main())
