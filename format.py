import discord
import datetime
import time
import asyncio
import random
import json
from discord.ext import commands
from discord.ext.commands import Bot
import youtube_dl
from itertools import cycle
import requests
import praw
import os
import aiohttp

Client = discord.client
client = commands.Bot(command_prefix = "m!")
client.remove_command('help')
Clientdiscord = discord.Client()
players = {}
queues= {}
 
def check_queue(id):
    if queues[id] != []:
        player = queues[id].pop(0)
        players[id] = player
        player.start()

@client.event
async def is_nsfw(channel: discord.Channel):
    try:
        _gid = channel.server.id
    except AttributeError:
        return False
    data = await client.http.request(
        discord.http.Route(
            'GET', '/guilds/{guild_id}/channels', guild_id=_gid))
    channeldata = [d for d in data if d['id'] == channel.id][0]
    return channeldata['nsfw']

@client.event
async def on_ready():
    print('------')
    print('Logged in as') 
    print(client.user.name) 
    print(client.user.id)
    
@client.command(pass_context=True)
async def userinfo(ctx, user: discord.Member):
  embed = discord.Embed(title="{}'s info".format(user.name), description='Here is what I could find:', color=0xff0000)
  embed.add_field(name='Name', value='{}'.format(user.name))
  embed.add_field(name='ID', value='{}'.format(user.id), inline=True)
  embed.add_field(name='Status', value='{}'.format(user.status), inline=True)
  embed.add_field(name='Highest Role', value='<@&{}>'.format(user.top_role.id), inline=True)
  embed.add_field(name='Joined at', value='{:%d/%h/%y at %H:%M}'.format(user.joined_at), inline=True)
  embed.add_field(name='Created at', value='{:%d/%h/%y at %H:%M}'.format(user.created_at), inline=True)
  embed.add_field(name='Discriminator', value='{}'.format(user.discriminator), inline=True)
  embed.add_field(name='Playing', value='{}'.format(user.game))
  embed.set_footer(text="{}'s Info".format(user.name), icon_url='{}'.format(user.avatar_url))
  embed.set_thumbnail(url=user.avatar_url)
  await client.say(embed=embed)
  
@client.command(pass_context=True)
async def serverinfo(ctx):
    server = ctx.message.server
    embed = discord.Embed(title="{}'s info".format(ctx.message.server.name), description="Here is what I could find:", color=0xff0000, timestamp=datetime.datetime.utcnow())
    embed.add_field(name="Name", value=ctx.message.server.name)
    embed.add_field(name="Server ID", value="`{}`".format(ctx.message.server.id))
    embed.add_field(name ="Members", value = str(server.member_count));
    embed.add_field(name="Roles", value='{}'.format(len(ctx.message.server.roles)))
    embed.set_thumbnail(url=ctx.message.server.icon_url)
    embed.set_footer(text="Requested by {}".format(ctx.message.author.name) + "#{}".format(ctx.message.author.discriminator), icon_url='{}'.format(ctx.message.author.avatar_url))
    await client.say(embed=embed)

@client.event
async def on_member_join(member):
    with open("users.json", "r") as f:
        users = json.load(f)

        await update_data(users, member)

        with open("users.json", "w") as f:
            json.dump(users, f)

@client.event
async def on_message(message):
    with open("users.json", "r") as f:
        users = json.load(f)

        if message.author.bot:
            return
        else:
            await update_data(users, message.author)
            number = random.randint(5,10)
            await add_experience(users, message.author, number)
            await level_up(users, message.author, message.channel)

        with open("users.json", "w") as f:
            json.dump(users, f)
    await client.process_commands(message)

async def update_data(users, user):
    if not user.id in users:
        users[user.id] = {}
        users[user.id]["experience"] = 0
        users[user.id]["level"] = 1

async def add_experience(users, user, exp):
    users[user.id]["experience"] += exp

async def level_up(users, user, channel):
    experience = users[user.id]["experience"]
    lvl_start = users[user.id]["level"]
    lvl_end = int(experience ** (1/4))

    if lvl_start < lvl_end:
        await client.send_message(channel, f":tada: Congratulations, {user.mention}, you leveled up to level {lvl_end}!")
        users[user.id]["level"] = lvl_end

@client.command(pass_context=True)
async def join(ctx):
    channel = ctx.message.author.voice.voice_channel
    await client.join_voice_channel(channel)
    await client.say('I have joined the Voice Channel!')
 
@client.command(pass_context=True)
async def leave(ctx):
    server = ctx.message.server
    voice_client = client.voice_client_in(server)
    await voice_client.disconnect()
    await client.say('I have left the Voice Channel!')
 
@client.command(pass_context=True)
async def play(ctx, url):
    server = ctx.message.server
    voice_client = client.voice_client_in(server)
    player = await voice_client.create_ytdl_player(url, after=lambda: check_queue(server.id))
    players[server.id] = player
    player.start()
    await client.say('I started playing the video!')
 
@client.command(pass_context=True)
async def pause(ctx):
    id = ctx.message.server.id
    players[id].pause()
    await client.say('I have paused the video!')
    
@client.command(pass_context=True)
async def resume(ctx):
    id = ctx.message.server.id
    players[id].resume()
    await client.say('I have resumed the video!')
    
@client.command(pass_context=True)
async def skip(ctx):
    id = ctx.message.server.id
    players[id].skip()
    await client.say('I have skipped the video!')
    
@client.command
async def queue(ctx, url):
    server = ctx.message.server
    voice_client = client.voice_client_in(server)
    player = await voice_client.create_ytdl_player(url, after=lambda: check_queue(server.id))
 
    if server.id in queues:
        queues[server.id].append(player)
    else:
        queues[server.id] = [player]
    await client.say('I have added the video in the queue!')

@client.command(pass_context=True)
async def mute(ctx, user: discord.Member = None):
    author = ctx.message.author
    try:
        if ctx.message.author.server_permissions.mute_members:
            if user is None:
                embed = discord.Embed(color=0xfc0d0e)
                embed.add_field(name=":red_circle: | User Check!", value="**Define a user! Please or this command is not worth your time!**")
                embed.set_footer(icon_url=author.avatar_url, text="User Check Is Necassary!")
                await client.say(embed=embed)
                return
            MutedRole = discord.utils.get(ctx.message.server.roles, name="Muted")
            await client.add_roles(user, MutedRole)
            embed = discord.Embed(color=0x439e1f)
            embed.add_field(name=":large_blue_circle:  | Mute Command activated!", value=f"{user.mention} Was sucessfuly muted!")
            embed.set_footer(icon_url=user.avatar_url, text="Activated!")
            await client.say(embed=embed)
        else:
            embed = discord.Embed(color=0xfc0d0e)
            embed.add_field(name=":red_circle: | Permission Check!", value=f"**{author.mention}, Please check your owner. You need Mute Members permissions.**")
            embed.set_footer(icon_url=author.avatar_url, text="Permission Check Is Necassary!")
            await client.say(embed=embed)
    except discord.Forbidden:
        embed = discord.Embed(color=0xfc0d0e)
        embed.add_field(name=":red_circle: | Permission Check!", value="**The muted role is Higher than me! Please move it to were I can mute members!**")
        embed.set_footer(icon_url=author.avatar_url, text="Permission Check Is Necassary!")
        await client.say(embed=embed)
        return
 
 
@client.command(pass_context=True)
async def unmute(ctx, user: discord.Member = None):
    author = ctx.message.author
    try:
        if ctx.message.author.server_permissions.mute_members:
            if user is None:
                embed = discord.Embed(color=0xfc0d0e)
                embed.add_field(name=":red_circle: | User Check!", value="**Define a user! Please or this command is not worth your time!**")
                embed.set_footer(icon_url=author.avatar_url, text="User Check Is Necassary!")
                await client.say(embed=embed)
                return
            MutedRole = discord.utils.get(ctx.message.server.roles, name="Muted")
            await client.remove_roles(user, MutedRole)
            embed = discord.Embed(color=0x439e1f)
            embed.add_field(name=":large_blue_circle:  | Unmute Command activated!", value=f"{user.mention} Was sucessfuly unmuted!")
            embed.set_footer(icon_url=user.avatar_url, text="Activated!")
            await client.say(embed=embed)
        else:
            embed = discord.Embed(color=0xfc0d0e)
            embed.add_field(name=":red_circle: | Permission Check!", value=f"**{author.mention}, Please check your owner. You need Mute Members permissions.**")
            embed.set_footer(icon_url=author.avatar_url, text="Permission Check Is Necassary!")
            await client.say(embed=embed)
    except discord.Forbidden:
        embed = discord.Embed(color=0xfc0d0e)
        embed.add_field(name=":red_circle: | Permission Check!", value="**The muted role is Higher than me! Please move it to were I can unmute members!**")
        embed.set_footer(icon_url=author.avatar_url, text="Permission Check Is Necassary!")
        await client.say(embed=embed)
        return

@client.command(pass_context=True)
async def clear(ctx, amount=None):
    author= ctx.message.author
    if ctx.message.author.server_permissions.manage_messages:
        if amount is None:
            embed = discord.Embed(color=0xfc0d0e)
            embed.add_field(name=":red_circle: | Amount Check!", value="**Define a amount! Please or this command is not worth your time!**")
            embed.set_footer(icon_url=author.avatar_url, text="Amount Check Is Necassary!")
            await client.say(embed=embed)
            return
        channel = ctx.message.channel
        author = ctx.message.author
        messages = []
        async for message in client.logs_from(channel, limit=int(amount)):
            messages.append(message)
        await client.delete_messages(messages)
        embed = discord.Embed(color=0xff00f0)
        embed.set_author(name='Clear - Information')
        embed.add_field(name='Amount:', value='**I have deleted {} messages**'.format(amount), inline=False)
        embed.add_field(name='Author:', value='**{}**'.format(author.name), inline=False)
        msg = await client.say(embed=embed)
        await asyncio.sleep(5)
        await client.delete_message(msg)
    else:
        embed = discord.Embed(color=0xfc0d0e)
        embed.add_field(name=":red_circle: | Permission Check!", value=f"**{author.mention}, Please check your owner. You need Manage Messages permissions.**")
        embed.set_footer(icon_url=author.avatar_url, text="Permission Check Is Necassary!")
        await client.say(embed=embed)
 
@client.command(pass_context=True)
async def kick(ctx, user: discord.Member = None):
    author = ctx.message.author
    try:
        if ctx.message.author.server_permissions.kick_members:
            if user is None:
                embed = discord.Embed(color=0xfc0d0e)
                embed.add_field(name=":red_circle: | User Check!", value="**Define a user! Please or this command is not worth your time!**")
                embed.set_footer(icon_url=author.avatar_url, text="User Check Is Necassary!")
                await client.say(embed=embed)
                return
            await client.kick(user)
            embed = discord.Embed(color=0x439e1f)
            embed.add_field(name=":large_blue_circle:  | Kick Command activated!", value=f"{user.mention} Was sadly kicked :(")
            embed.set_footer(icon_url=user.avatar_url, text="Activated!")
            await client.say(embed=embed)
        else:
            embed = discord.Embed(color=0xfc0d0e)
            embed.add_field(name=":red_circle: | Permission Check!", value=f"**{author.mention}, Please check your owner. You need Kick Members permissions.**")
            embed.set_footer(icon_url=author.avatar_url, text="Permission Check Is Necassary!")
            await client.say(embed=embed)
    except discord.Forbidden:
        embed = discord.Embed(color=0xfc0d0e)
        embed.add_field(name=":red_circle: | Permission Check!", value="**I can't kick this member or bot because he/she is a higher rank or higher permission than me!**")
        embed.set_footer(icon_url=author.avatar_url, text="Permission Check Is Necassary!")
        await client.say(embed=embed)
 
@client.command(pass_context=True)
async def ban(ctx, user: discord.Member = None):
    author = ctx.message.author
    try:
        if ctx.message.author.server_permissions.ban_members:
            if user is None:
                embed = discord.Embed(color=0xfc0d0e)
                embed.add_field(name=":red_circle: | User Check!", value="**Define a user! Please or this command is not worth your time!**")
                embed.set_footer(icon_url=author.avatar_url, text="User Check Is Necassary!")
                await client.say(embed=embed)
                return
            await client.ban(user)
            embed = discord.Embed(color=0x439e1f)
            embed.add_field(name=":large_blue_circle:  | Ban Command activated!", value=f"{user.mention} Was banned!")
            embed.set_footer(icon_url=user.avatar_url, text="Activated!")
            await client.say(embed=embed)
        else:
            embed = discord.Embed(color=0xfc0d0e)
            embed.add_field(name=":red_circle: | Permission Check!", value=f"**{author.mention}, Please check your owner. You need Ban Members permissions.**")
            embed.set_footer(icon_url=author.avatar_url, text="Permission Check Is Necassary!")
            await client.say(embed=embed)
    except discord.Forbidden:
        embed = discord.Embed(color=0xfc0d0e)
        embed.add_field(name=":red_circle: | Permission Check!", value="**I can't ban this member or bot because he/she is a higher rank or higher permission than me!**")
        embed.set_footer(icon_url=author.avatar_url, text="Permission Check Is Necassary!")
        await client.say(embed=embed)

@client.command(pass_context=True)
async def unban(ctx, user: discord.Member = None):
    author = ctx.message.author
    try:
        if ctx.message.author.server_permissions.ban_members:
            if user is None:
                embed = discord.Embed(color=0xfc0d0e)
                embed.add_field(name=":red_circle: | User Check!", value="**Define a user! Please or this command is not worth your time!**")
                embed.set_footer(icon_url=author.avatar_url, text="User Check Is Necassary!")
                await client.say(embed=embed)
                return
            await client.unban(user)
            embed = discord.Embed(color=0x439e1f)
            embed.add_field(name=":large_blue_circle:  | Unban Command activated!", value=f"{user.mention} Was unbanned!")
            embed.set_footer(icon_url=user.avatar_url, text="Activated!")
            await client.say(embed=embed)
        else:
            embed = discord.Embed(color=0xfc0d0e)
            embed.add_field(name=":red_circle: | Permission Check!", value=f"**{author.mention}, Please check your owner. You need Ban Members permissions.**")
            embed.set_footer(icon_url=author.avatar_url, text="Permission Check Is Necassary!")
            await client.say(embed=embed)
    except discord.Forbidden:
        embed = discord.Embed(color=0xfc0d0e)
        embed.add_field(name=":red_circle: | Permission Check!", value="**I can't ban this member or bot because he/she is a higher rank or higher permission than me!**")
        embed.set_footer(icon_url=author.avatar_url, text="Permission Check Is Necassary!")
        await client.say(embed=embed)

client.run(str(os.environ.get('NTY2NzA4OTgyNzI3NzA0NTc2.XLI7Mw.f5hUnZPWH7Y-tgu4Imtrc6EPmo8')))
