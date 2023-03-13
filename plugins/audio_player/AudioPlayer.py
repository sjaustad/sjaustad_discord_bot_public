from mimetypes import init
from sys import stdout
import os, time, discord
from settings.server_settings import settings
settings = settings()
from discord import FFmpegPCMAudio, PCMVolumeTransformer
from gtts import  gTTS
import asyncio
from discord.utils import get

from utils.database.calls.music_history import MusicHistory


class audio_controller:
    def __init__(self, bot):

        ## Instances
        self.music_db = MusicHistory(bot.redis)
        self.queue_list = []
        self.event_loop = None
        self.current_voice_channel = None
        self.current_audio = None
        self.voice = None
        self.skip_next = False
        self.stop = False
        self.counter = 0
        self.timer_coroutine = None
        self.muted = False
        self.bot=bot
        self.FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}
        self.transcription_sess=False

        

    ## Definition variables
    max_audio_length = 36000 # In seconds
    stream_threshold = 3600
    min_audio_length = 0.1 # In seconds
    max_queue_length = 25

    ## Functions
    async def start_audio_listener(self, initial = False):
        ## on start delete queue
        if initial is True:
            await self.music_db.delete_queue()
            return


        while True:
            ## get the queue list
            self.queue_list = await self.music_db.retrieve_queue()
            print("Checking audio queue...")

            if (len(self.queue_list) <= 0 and self.voice is not None) or self.stop is True:
                print("Found new audio to play...")

                stop_audio = True
                if self.current_audio is not None:
                    if 'loop' in self.current_audio:
                        ## this is where we determine if we loop
                        if self.current_audio['loop'] is True and self.stop is not True:
                            stop_audio = False
                            if (self.voice.is_playing() is True and self.skip_next is False) or self.voice.is_paused(): 
                                pass
                            ## LOOP ##
                            ## this is where we add the song back to the queue
                            else:
                                ## add to redis database queue
                                await self.music_db.add_to_queue(self.current_audio)
                                ##self.queue_list.append(self.current_audio)

                if stop_audio is True:
                    # make sure that the bot is not playing and is not paused
                    if self.voice:
                        ## STOP ##
                        ## this is where we stop
                        if not self.voice.is_playing() and not self.voice.is_paused():

                            # Queue is empty and nothing is playing. Close down listener

                            self.stop = False
                            await self.voice.disconnect()
                            self.voice = None
                            ## clean up session files
                            audio_dir = f"{settings.server.base_dir}/audio_files"
                            try:
                                for f in os.listdir(audio_dir):
                                    os.remove(os.path.join(audio_dir, f))
                            except PermissionError:
                                pass # file in lock because user cancelled request

                            self.muted=False
                            await self.music_db.delete_queue()



                            self.timer_coroutine.cancel()
                            self.voice = None
                            self.current_voice_channel = None
                            self.current_audio = None

                            break
            if len(self.queue_list) <= 0:
                print(f"Nothing in the queue. Exiting loop...")
                break
            for item in self.queue_list:
                ## Check if voice attribute is null, if it is then proceed to play media
                if self.voice is not None:
                    ## Check if voice is active
                    isPlaying = self.voice.is_playing()
                    if (isPlaying is True and self.skip_next is False) or self.voice.is_paused(): 
                       #break
                       continue
                    ## SKIP ##
                    ## this is where we skip if needed
                    else: 
                        try:
                            #await self.voice.disconnect()
                            isPlaying = None

                            self.voice.stop()
                            self.counter = 0
                            self.timer_coroutine.cancel()

                        except Exception as e:
                            break
                            #continue
                else:
                    ## Voice is not active, reset isPlaying variable
                    isPlaying = None
                if not isPlaying:
                    self.counter = 0
                    replay= False
                    if self.current_audio is not None:
                        if 'loop' in self.current_audio:
                            if self.current_audio['loop'] is True:
                                replay = True
                    if replay is True:
                        next_track = self.current_audio
                    else:
                        next_track = item
                    self.skip_next = False
                    connect_channel = True
                    if self.current_voice_channel is not None:
                        if self.current_voice_channel.id == next_track['channel_id'] and self.voice != None:
                            connect_channel = False
                        else:
                            voice_channel = self.bot.get_channel(next_track['channel_id'])
                            self.current_voice_channel = voice_channel
                    else:
                        voice_channel = self.bot.get_channel(next_track['channel_id'])
                        self.current_voice_channel = voice_channel
                    #try:

                    ## This case is for streaming audio directly
                    if next_track['stream'] is False and next_track['tts'] is False:

                        if connect_channel is True:
                            try:
                                self.voice = await self.current_voice_channel.connect()
                            except:
                                try:
                                #errorLogger("AudioPlayer.py","Failed to connect to audio channel trying again...")
                                    self.voice = await self.current_voice_channel.connect()
                                except (discord.ClientException):
                                    pass ## already connected to voice

                        ## get last audio
                        volume = await self.music_db.get_volume()
                        ## PLAY AUDIO ##
                        self.voice.play(PCMVolumeTransformer(FFmpegPCMAudio(next_track['file_name']), volume=volume))

                        ## try to cancel old timer ##
                        try:
                            self.timer_coroutine.cancel()
                        except: 
                            pass

                        ## Start timer ##
                        self.timer_coroutine = asyncio.create_task(self.timer((next_track['audio_obj']['duration']), next_track))
                    
                    ## this case is for doing text to speech (either transribe or say)
                    elif item['tts'] is True:
                        ## Initialize voice engine
                        """
                        engine = pyttsx3.init("sapi5")
                        voices = engine.getProperty("voices")[1] 
                        engine.setProperty('rate', 125)  
                        engine.setProperty('voice', voices)
                        ## Create audio file
                        engine.save_to_file(item['speech_text'], item['link'])
                        engine.runAndWait() 
                        engine.stop()
                        """
                        tts_obj = gTTS(text=item['speech_text'], lang=item['language'], slow=False, tld=item['tld'])
                        tts_obj.save(item['link'])
                        if connect_channel is True:
                            self.voice = await self.current_voice_channel.connect()
                        self.voice.play(FFmpegPCMAudio(item['link']))
                    
                    else:
                        pass
                        if connect_channel is True:
                            self.voice = await self.current_voice_channel.connect()
                        self.voice.play(FFmpegPCMAudio(URL))#, **self.FFMPEG_OPTIONS))
                    self.current_audio = item
                    self.voice.is_playing()
                    #except:
                    #    errorLogger(thisFunction,f"Could not play audio for {item['link']}")
                    ##self.queue_list.pop(0)
                    ## remove the first element from queue
                    await self.music_db.remove_first_from_queue()

                    break
                    #continue
                else:
                    #continue
                    break
            await asyncio.sleep(5)

    async def timer(self, length, audio_info):
        #for x in range (0, length):
        try:
            while self.counter < length:
                if self.voice:
                    if not self.voice.is_paused():
                        ## if we cancel this coroutine, then except
                        # try:
                        #     await asyncio.sleep(2)
                        # except asyncio.CancelledError:
                        #     break
                        await asyncio.sleep(2)
                        self.counter += 2
                    else:
                        await asyncio.sleep(2)
                else:
                    return False
        except asyncio.CancelledError:
            pass
        self.counter = 0
        if not audio_info['loop']:
            await self.music_db.store_history(audio_info)
        ## store last volume
        try:
            volume = self.voice.source.volume
            await self.music_db.store_volume(volume)
        except:
            pass
        return True

    async def add_to_queue(self, bot, voice_channel, author_info, stream, audio_obj=None, link= None, speech_text=None, tts=False, language=None, tld=None):



        #if self.current_voice_channel is None:
        #    await self.music_db.delete_queue()

        if not os.path.isdir("audio_files"):
            os.mkdir("audio_files")
        timestamp = time.time()
        if tts is False:
            pass

        else:
            tts_file = 'audio_files/speech_tts.mp3'

            audio_dict = {
                "channel_id":voice_channel.id,
                "link":tts_file,
                "requestor_id":author_info.id,
                "requestor_name":author_info.name,
                "stream":stream,
                "tts":True,
                "speech_text":speech_text,
                "language":language,
                "tld":tld
            }
        
        ## add to queue in database
        await self.music_db.add_to_queue(audio_dict)
        
        ##self.queue_list.append(audio_dict)

        if self.voice is None: 

            try:
                voice_client = get(bot.voice_clients, guild=voice_channel.guild)
            except:
                voice_client = None

            if voice_client is not None:
                try:
                    await voice_client.disconnect()
                except:
                    pass
            return_var = True
        else: return_var = False

        ## check to see if the queue check is running
        ## if it's not, start it up
        if self.event_loop is None and self.voice is None:
            ## start up event loop
            print("Audio listener not running. Starting up...")
            self.event_loop = bot.loop.create_task(self.start_audio_listener())
        elif type(self.event_loop) == asyncio.Task:
            ## start event loop if it's been finished or cancelled
            if self.event_loop._state == "CANCELLED":
                print("Audio listener not running. Starting up...")
                self.event_loop = bot.loop.create_task(self.start_audio_listener())
            if self.event_loop._state == "FINISHED":
                print("Audio listener not running. Starting up...")
                self.event_loop = bot.loop.create_task(self.start_audio_listener())
        else:
            ## I don't know what's going on
            ## somehow the event_loop became something it shouldn't have 
            return False


        return return_var

        
        
    async def get_audio_info(self, link):
        pass
