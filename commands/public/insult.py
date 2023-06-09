import discord, traceback, random
from discord import app_commands
from discord.ext import commands

class Insult_cog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="insult", description="insult someone")
    async def insult(self, interaction: discord.Interaction, user: discord.User, user2: discord.User = None, user3: discord.User = None, user4: discord.User = None, user5: discord.User = None):
        reponse_array = ["Light travels faster than sound. This is why some people appear bright until they speak.",
        "When people ask me stupid questions, it is my legal obligation to give a sarcastic remark.",
        "It’s okay if you don’t like me. Not everyone has good taste.",
        "You look good when your eyes are closed, but you look the best when my eyes closed.",
        "Mirrors can’t talk, lucky for you they can’t laugh either.",
        "If had a dollar for every smart thing you say. I’ll be poor.",
        "I don’t believe in plastic surgery. But in your case, go ahead.",
        "Are you always so stupid or is today a special occassion?",
        "I feel so miserable without you, it’s almost like having you here.",
        "If you find me offensive. Then I suggest you quit finding me.",
        "Everyone seems normal until you get to know them.",
        "If I wanted to kill myself I would climb your ego and jump to your IQ.",
        "I don’t have the energy to pretend to like you today.",
        "I’m not saying I hate you, what I’m saying is that you are literally the Monday of my life.",
        "I’m sorry I hurt your feelings when I called you stupid. I really thought you already knew.",
        "Sarcasm – the ability to insult idiots without them realizing it.",
        "Unless your name is Google stop acting like you know everything.",
        "Yet despite the look on my face… you are still talking.",
        "Find your patience before I lose mine.",
        "Just because I don’t care doesn’t mean I don’t understand.",
        "Sometimes I need what only you can provide: your absence.",
        "Always remember that you’re unique. Just like everyone else.",
        "Silence is golden. Duct tape is silver.",
        "I’d tell you to go to hell, but I work there and don’t want to see your ugly mug every day.",
        "I never forget a face, but in your case, I’ll be glad to make an exception.",
        "Everyone has the right to be stupid, but you are abusing the privilege.",
        "People say that laughter is the best medicine… your face must be curing the world.",
        "If at first, you don’t succeed, skydiving is not for you.",
        "My imaginary friend says that you need a therapist.",
        "Let’s share… You’ll take the grenade, I’ll take the pin.",
        "Fighting with me is like being in the special olympics. You may win, but in the end you’re still a retard.",
        "Well at least your mom thinks you’re pretty.",
        "My neighbor’s diary says that I have boundary issues.",
        "Just because the voices only talk to me doesn’t mean you should get all jealous. You’re just a little too crazy for their taste.",
        "Don’t worry about what people think. They don’t do it very often.",
        "If you think nobody cares if you’re alive, try missing a couple of car payments.",
        "I clapped because it’s finished, not because I like it.",
        "I’m not listening, but keep talking. I enjoy the way your voice makes my ears bleed.",
        "I’m not sarcastic. I’m just intelligent beyond your understanding.",
        "I am busy right now, can I ignore you some other time?",
        "That is the ugliest top I’ve ever seen, yet it compliments your face perfectly.",
        "Life’s good, you should get one.",
        "No, you don’t have to repeat yourself. I was ignoring you the first time.",
        "I’m sorry while you were talking I was trying to figure where the hell you got the idea I cared.",
        "Just keep talking, I yawn when I’m interested.",
        "Well, my imaginary friend thinks you have serious mental problems.",
        "Cancel my subscription because I don’t need your issues.",
        "Me pretending to listen should be enough for you.",
        "If you’re waiting for me to give a shit, you better pack a lunch. It’s going to be while.",
        "Ugliness can be fixed, stupidity is forever.",
        "Zombies eat brains. You’re safe.",
        "Are you always this retarded or are you making a special effort today?",
        "You’d be in good shape… if you ran as much as your mouth.",
        "If karma doesn’t hit you, I gladly will.",
        "Keep rolling your eyes. Maybe you’ll find a brain back there.",
        "You always do me a favor, when you shut up!",
        "Tell me how I have upset you, because I want to know how to do it again.",
        "I’m not crazy! The voices tell me I am entirely sane.",
        "Sure I’ll help you out… the same way you came in.",
        "Shut your mouth when you’re talking to me.",
        "I’d agree with you but then we’d both be wrong.",
        "Think I am sarcastic? Watch me pretend to care!",
        "My friends are so much cooler than yours. They’re invisible.",
        "If it looks like I give a damn, please tell me. I don’t want to give off the wrong impression.",
        "You sound better with your mouth closed.",
        "If ignorance is bliss. You must be the happiest person on this planet.",
        "I’m smiling… that alone should scare you.",
        "If you wrote down every single thought you ever had you would get an award for the shortest story ever.",
        "If I promise to miss you, will you go away?",
        "I’ll try being nicer, if you try being smarter.",
        "Thank you for leaving my side when I was alone. I realized I can do so much without you."]

        ## Get the author's voice channel
        try:
            voice_channel = interaction.user.voice.channel
            do_voice = True
        except:
            do_voice = False

        user_mentions = [user]

        if user2: user_mentions.append(user2)
        if user3: user_mentions.append(user3)
        if user4: user_mentions.append(user4)
        if user5: user_mentions.append(user5)


        random_response = random.choice(reponse_array)

        user_mentions_text = ""

        name_list = []
        for user in user_mentions:
            if user.id == self.bot.application_id: return await interaction.response.send_message(f"Nice try, {interaction.user.mention}. {random_response}")
            user_mentions_text += user.mention
            user_mentions_text += " "
            name_list.append(user.name)

        await interaction.response.send_message(f"{user_mentions_text} {random_response}")

        if do_voice is True:
            speech_text = random_response
            language = "en"
            tld="com"

            name_str = "Hey, "
            if len(name_list) > 1:
                for name in name_list:
                    if name_list[-1] == name:
                        name_str+= "and" + name
                    else:
                        name_str+= name + ", "
            else:
                name_str += name_list[0]
            
            speech_text = name_str + speech_text

            stream= False 
            status = await self.bot.audio_controller.add_to_queue(self.bot, voice_channel, interaction.user, stream, speech_text=speech_text, tts=True, language=language, tld=tld)
            if status is False: await interaction.followup.send(content= f"{interaction.user.mention}, your audio has been added to the queue.", ephemeral=True)            

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Insult_cog(bot))