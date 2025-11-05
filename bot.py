import sys, glob, importlib, logging, logging.config, pytz, asyncio
from pathlib import Path

# Get logging configurations
logging.config.fileConfig('logging.conf')
logging.getLogger().setLevel(logging.INFO)
logging.getLogger("pyrogram").setLevel(logging.ERROR)
logging.getLogger("cinemagoer").setLevel(logging.ERROR)

from pyrogram import Client, idle
from database.users_chats_db import db
from info import *
from utils import temp
from typing import Union, Optional, AsyncGenerator
from Script import script 
from datetime import date, datetime 
# from aiohttp import web - Removed Stream
# from plugins import web_server - Removed Stream

from Qwerty.bot import QwertyBot
# from TechVJ.util.keepalive import ping_server - Removed Stream
from Qwerty.bot.clients import initialize_clients

ppath = "plugins/*.py"
files = glob.glob(ppath)
# TechVJBot.start() - Error: Must be called inside async function
loop = asyncio.get_event_loop()


async def start():
    print('\n')
    print('Initalizing Your Bot')
    
    # --- FIX: Start the bot inside the async function ---
    await QwertyBot.start()
    
    bot_info = await QwertyBot.get_me()
    await initialize_clients()
    for name in files:
        with open(name) as a:
            patt = Path(a.name)
            plugin_name = patt.stem.replace(".py", "")
            plugins_dir = Path(f"plugins/{plugin_name}.py")
            import_path = "plugins.{}".format(plugin_name)
            spec = importlib.util.spec_from_file_location(import_path, plugins_dir)
            load = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(load)
            sys.modules["plugins." + plugin_name] = load
            print("Qwerty Imported => " + plugin_name)
            
    # --- REMOVED: ping_server() as it's part of the stream/web feature ---
    # if ON_HEROKU:
    #     asyncio.create_task(ping_server())
        
    b_users, b_chats = await db.get_banned()
    temp.BANNED_USERS = b_users
    temp.BANNED_CHATS = b_chats
    me = await TechVJBot.get_me()
    temp.BOT = TechVJBot
    temp.ME = me.id
    temp.U_NAME = me.username
    temp.B_NAME = me.first_name
    logging.info(script.LOGO)
    tz = pytz.timezone('Asia/Kolkata')
    today = date.today()
    now = datetime.now(tz)
    time = now.strftime("%H:%M:%S %p")
    
    try:
        await QwertyBot.send_message(chat_id=LOG_CHANNEL, text=script.RESTART_TXT.format(today, time))
    except Exception as e:
        print(f"Error sending restart message to LOG_CHANNEL: {e}")
        print("Make Your Bot Admin In Log Channel With Full Rights")
        
    for ch in CHANNELS:
        try:
            k = await QwertyBot.send_message(chat_id=ch, text="**Bot Restarted**")
            await k.delete()
        except Exception as e:
            print(f"Error sending restart message to CHANNELS ({ch}): {e}")
            print("Make Your Bot Admin In File Channels With Full Rights")
            
    if AUTH_CHANNEL:
        try:
            k = await QwertyBot.send_message(chat_id=AUTH_CHANNEL, text="**Bot Restarted**")
            await k.delete()
        except Exception as e:
            print(f"Error sending restart message to AUTH_CHANNEL: {e}")
            print("Make Your Bot Admin In Force Subscribe Channel With Full Rights")
            
    if CLONE_MODE == True:
        print("Restarting All Clone Bots.......")
        await restart_bots()
        print("Restarted All Clone Bots.")
        
    # --- REMOVED: Web server setup ---
    # app = web.AppRunner(await web_server())
    # await app.setup()
    # bind_address = "0.0.0.0"
    # await web.TCPSite(app, bind_address, PORT).start()
    
    print("Bot Started Successfully!")
    await idle()


if __name__ == '__main__':
    try:
        loop.run_until_complete(start())
    except KeyboardInterrupt:
        logging.info('Service Stopped Bye 👋')

