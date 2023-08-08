import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import discord
from discord.ext import commands
from discord import FFmpegPCMAudio
from listennotes import podcast_api
import asyncio

# Configuration
PODCAST_API_KEY = os.environ.get('PODCAST_API_KEY')
SPOTIPY_CLIENT_ID = os.environ.get('SPOTIPY_CLIENT_ID')
SPOTIPY_CLIENT_SECRET = os.environ.get('SPOTIPY_CLIENT_SECRET')
SPOTIPY_REDIRECT_URI = os.environ.get('SPOTIPY_REDIRECT_URI')
DISCORD_BOT_TOKEN = os.environ.get('DISCORD_BOT_TOKEN')
CHANNEL_ID = os.environ.get('BOT_CHANNEL')

# Initialize APIs
podsearchclient = podcast_api.Client(api_key=PODCAST_API_KEY)
scope = "user-read-playback-state,user-modify-playback-state, streaming"
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET, redirect_uri=SPOTIPY_REDIRECT_URI, scope=scope))

# Global Variables
queues = []
currentShow = []

# Discord Bot Setup
client = discord.Client()
bot = commands.Bot('-')
FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')

@bot.command()
async def play(ctx, args):
    if (ctx.author.voice): # If the person is in a channel
        epinfo = sp.episode(args)
        print(epinfo)

        name = epinfo['name']
        desc = epinfo['description']
        show = epinfo['show']['name']
        showid = epinfo['show']['id']
        currentepid = epinfo['id']

        searchstring = name.strip().lower() + ' ' + show.strip().lower()
        searchresult = podsearchclient.search(q=searchstring)
        if not len(searchresult.json()['results']):
            searchresult = podsearchclient.search(q=name.strip)
        if not len(searchresult.json()['results']):
            await ctx.send(
                "Found episode but the audio file is unreachable for some reason. Use -play to play another episode")
        print(searchresult.json()['results'])
        listdoop = searchresult.json()['results'][0]['audio']

        currentShow.clear()

        currentShow.append(show)
        currentShow.append(showid)
        currentShow.append(currentepid)

        print(currentShow)

        if ctx.voice_client is not None and (ctx.voice_client.is_playing() or ctx.voice_client.is_paused()):
            await ctx.send('**Adding to queue: **' + name + "\n\n")
            queues.append([listdoop, name, desc, show, showid, currentepid])
        else:
            if ctx.voice_client is None:
                channel = ctx.author.voice.channel
                player = await channel.connect()
                await ctx.send('**Thanks for using Pod Bot!\nI try my best but i still have a little trouble sometimes, so please take care not to overwhelm me.\nDont use *-next* when the queue is empty, its hard for me to handle.\nIf im autoplaying and you want to end it, add an episode to the queue with *-play* and then use *-next*, or just disconnect me, I wont take it personally')
            print(searchstring)
            await ctx.send('**Now playing: **'+ name +'\n\n' + desc + '\n\n')
            player.play(FFmpegPCMAudio(listdoop, **FFMPEG_OPTIONS), after=lambda e: asyncio.run_coroutine_threadsafe(next(ctx), bot.loop))
    else: #But is (s)he isn't in a voice channel
        await ctx.send("You must be in a voice channel first so I can join it.\n\n")


@bot.command()
async def stop(ctx):
    if ctx.voice_client:  # If the bot is in a voice channel
        await ctx.guild.voice_client.disconnect()  # Leave the channel
    else: # But if it isn't
        await ctx.send("I'm not in a voice channel, use the join command to make me join\n\n")

@bot.command()
async def next(ctx):
    if ctx.voice_client:
        player = ctx.voice_client
        if player.is_playing():
            player.stop()
        if len(queues) > 0:
            player.play(FFmpegPCMAudio(queues[0][0], **FFMPEG_OPTIONS), after= lambda e: asyncio.run_coroutine_threadsafe(next(ctx), bot.loop))
            await ctx.send('**Now playing: **'+ queues[0][1] +'\n\n' + queues[0][2] + "\n\n")
            currentShow.clear()
            currentShow.append(queues[0][3])
            currentShow.append(queues[0][4])
            currentShow.append(queues[0][5])
            queues.remove(queues[0])
        else:
            print('Getting next episode now')
            #await ctx.send("Getting next episode of the currently playing podcast\n\n")
            offsetnum = 0
            found = False
            while True:
                print("Checking with offset: " + str(offsetnum))
                currentshowinfo = sp.show_episodes(show_id=currentShow[1], limit=50, offset=offsetnum)
                for x in currentshowinfo['items']:
                    if x['id'] == currentShow[2]:
                        print("FOUND IT")
                        found = True
                        break
                if found is True:
                    break
                offsetnum += 49

            currentshowinfo2 = sp.show_episodes(show_id=currentShow[1], limit=50, offset=offsetnum)
            for x in currentshowinfo2['items']:
                if x['id'] == currentShow[2]:
                    print('EPISODE FOUND AT POSITION: ' + str(currentshowinfo2['items'].index(x)))
                    if currentshowinfo2['items'].index(x) != 0:
                        nextepid = currentshowinfo2['items'][currentshowinfo2['items'].index(x) - 1]['id']
                        print('CURRENT EPISODE AT INDEX: ' + str(currentshowinfo2['items'].index(x)))
                        print('Next episode at index: ' + str(currentshowinfo2['items'].index(x) - 1))
                        print("NEXT EPISODE LINK\n\n\n")
                        nexteplink = currentshowinfo2['items'][currentshowinfo2['items'].index(x) - 1]['external_urls'][
                            'spotify']
                        print(nexteplink)
                        epinfo = sp.episode(nexteplink)
                        print(epinfo)

                        name = epinfo['name']
                        desc = epinfo['description']
                        show = epinfo['show']['name']
                        showid = epinfo['show']['id']
                        currentepid = epinfo['id']

                        searchstring2 = name.strip().lower() + ' ' + show.strip().lower()
                        searchresult2 = podsearchclient.search(q=searchstring2)
                        print(searchstring2)
                        if not len(searchresult2.json()['results']):
                            print("lIST IS EMPTY")
                            searchresult2 = podsearchclient.search(q=name.strip())
                        if not len(searchresult2.json()['results']):
                            await ctx.send("Found episode but the audio file is unreachable for some reason. Use -play to play another episode")
                        print(searchresult2.json()['results'])
                        listdoop3 = searchresult2.json()['results'][0]['audio']

                        currentShow.clear()

                        currentShow.append(show)
                        currentShow.append(showid)
                        currentShow.append(currentepid)

                        print(currentShow)
                        print(searchstring2)
                        await ctx.send('**Now playing: **' + name + '\n\n' + desc + "\n\n")
                        player.play(FFmpegPCMAudio(listdoop3, **FFMPEG_OPTIONS),
                                    after=lambda e: asyncio.run_coroutine_threadsafe(next(ctx), bot.loop))
                    else:
                        print("Current episode is most recent")
                        await ctx.send("No newer episodes of show found. Use -play to add more episodes to queue\n\n")
                        player.disconnect()


            print("Getnextep done")
    else:
        await ctx.send("I'm not in a voice channel, use the join command to make me join\n\n")

@bot.command()
async def pause(ctx):
    if ctx.voice_client:
        player = ctx.voice_client
        if ctx.voice_client.is_playing():
            player.pause()
            await ctx.send('Paused, use -pause again to resume playback\n')
        else:
            player.resume()
            await ctx.send('Resumed\n')
    else:
        await ctx.send("I'm not in a voice channel, use the join command to make me join\n\n")


@bot.command()
async def queue(ctx):
    if len(queues) > 0:
        message = ''
        position = 1
        for x in queues:
            message += (str(position) + ': ' + x[1] + '\n\n')
            position += 1
        await ctx.send("**Episode Queue:**\n"+message)
    else:
        await ctx.send('You have nothing in your Queue, use -play to add episodes\n\n')

if __name__ == '__main__':
    bot.run(DISCORD_BOT_TOKEN)
