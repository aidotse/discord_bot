import discord
from discord.ext import commands
import requests
import json
from collections import defaultdict
from datetime import datetime, timedelta
import asyncio
import random
import pytz

bot = commands.Bot(command_prefix='!', intents=discord.Intents.default())
conversations = defaultdict(lambda: {"history": [], "last_update": datetime.now()})

# Lunch and Friday messages
lunch_messages = ["Vi på jobbet behöver veta vart vi ska äta lunch på Södermalm, gärna nära Medborgarplatsen, ge oss ett tips på resturang, inte fler, bara ett tips till oss. Nämn resturangen. Inled meningen med: Här är ett tips på lunch"]
friday_messages = ["Önska alla en trevlig helg och säg att dom jobbat bra, var kortfattad."]

def get_gpt_sw3_response(conversation):
    url = 'https://gpt.ai.se/v1/engines/gpt-sw3/chat/completions'
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json'
    }
    payload = {
        "model": "gpt-sw3-20b-instruct",
        "messages": conversation,
        "max_tokens": 768,
        "temperature": 0.8,
        "top_p": 1,
        "n": 1,
        "stream": False,
        "stop": ["<s>"],
        "logit_bias": {},
        "presence_penalty": 0,
        "frequency_penalty": 0,
        "user": "ai_sweden",
        "token": "6p3T5QW4gu2FDsJfVmmPvS26HNT478uj"
    }

    response = requests.post(url, headers=headers, data=json.dumps(payload))
    return response.json()

async def clear_old_conversations():
    while True:
        current_time = datetime.now()
        for user_id in list(conversations.keys()):
            if current_time - conversations[user_id]["last_update"] > timedelta(minutes=60*4):
                del conversations[user_id]
        await asyncio.sleep(60)

channel_ids = [911287092586356787, 1070643520727171154]
#channel_ids = [1070643520727171154]


@bot.command()
async def send_dm(ctx, user_id: int, *, prompt: str):
    print("send_dm command invoked")
    if not isinstance(ctx.channel, discord.channel.DMChannel):
        await ctx.send("This command can only be used in direct messages.")
        return

    conversation = [{"role": "user", "content": prompt}]
    print("!send_dm_input", conversation, user_id)

    api_response = get_gpt_sw3_response(conversation)
    if api_response and api_response.get('choices'):
        gpt_message = api_response['choices'][0]['message']['content']
        print("!send_dm_response", gpt_message, user_id)
    else:
        await ctx.send("Sorry, I couldn't generate a response.")
        return

    user = await bot.fetch_user(user_id)
    if user:
        try:
            await user.send(gpt_message)
            await ctx.send(f"Message sent to {user.display_name}.")
        except discord.errors.Forbidden:
            await ctx.send("I can't send a message to this user.")
    else:
        await ctx.send("User not found.")

async def send_scheduled_message():
    now = datetime.now(pytz.timezone('Europe/Stockholm'))

    next_run_time = now + timedelta(days=1)
    next_run_time = next_run_time.replace(hour=11, minute=random.randint(15, 30), second=0, microsecond=0)

    if now.weekday() < 5:
        lunch_time_today = now.replace(hour=11, minute=random.randint(15, 30), second=0, microsecond=0)
        if now < lunch_time_today:
            next_run_time = lunch_time_today
        message_list = lunch_messages

    elif now.weekday() == 4:
        friday_message_time = now.replace(hour=15, minute=random.randint(30, 45), second=0, microsecond=0)
        if now < friday_message_time:
            next_run_time = friday_message_time
        message_list = friday_messages

    wait_seconds = (next_run_time - now).total_seconds()
    await asyncio.sleep(wait_seconds)

    for channel_id in channel_ids:
        channel = bot.get_channel(channel_id)
        if channel:
            initial_message = random.choice(message_list)
            conversation = [{"role": "user", "content": initial_message}]
            api_response = get_gpt_sw3_response(conversation)
            if api_response and api_response.get('choices'):
                assistant_message = api_response['choices'][0]['message']['content']
                await channel.send(assistant_message)

    bot.loop.create_task(send_scheduled_message())

@bot.event
async def on_message(message):
    if message.author == bot.user or message.author.bot:
        return

    if bot.user.mentioned_in(message):
        user_id = message.author.id
        conversation = conversations[user_id]["history"]

        if not conversation:
            conversation.append({"role": "assistant", "content": "Hi, I am your helpful assistant."})

        conversation.append({"role": "user", "content": message.content})

        api_response = get_gpt_sw3_response(conversation)
        if api_response and api_response.get('choices'):
            assistant_message = api_response['choices'][0]['message']['content']
            conversation.append({"role": "assistant", "content": assistant_message})
            await message.channel.send(assistant_message)
        else:
            await message.channel.send("Sorry, I couldn't process that.")

        conversations[user_id]["last_update"] = datetime.now()
        print("conversation:", conversation)

    await bot.process_commands(message)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    for guild in bot.guilds:
        print(f'Guild: {guild.name}')
        for channel in guild.channels:
            print(f' - {channel.name} ({channel.id})')
    bot.loop.create_task(send_scheduled_message())

bot.run('MTE4Mzg1MDA5OTg4MTgyMDIwMA.GjgFkO.B21SV9U5IhdV4XxMGEBFw_Cz97FKk3cArYzZlg')
