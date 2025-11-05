import os, logging, asyncio, time, re, ast, random, math, pytz
from datetime import datetime, timedelta
from Script import script
from info import *
from pyrogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, 
    InputMediaPhoto, ChatPermissions, WebAppInfo
)
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait, UserIsBlocked, MessageNotModified, PeerIdInvalid
from pyrogram.errors.exceptions.bad_request_400 import MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty
from utils import (
    get_size, is_subscribed, pub_is_subscribed, get_poster, 
    search_gagala, temp, get_settings, save_group_settings, 
    get_shortlink, get_tutorial, send_all, get_cap
)
from database.users_chats_db import db
from database.ia_filterdb import col, sec_col, db as vjdb, sec_db, get_file_details, get_search_results, get_bad_files
from database.filters_mdb import del_all, find_filter, get_filters
from database.connections_mdb import mydb, active_connection, all_connections, delete_connection, if_active, make_active, make_inactive
from database.gfilters_mdb import find_gfilter, get_gfilters, del_allg
from urllib.parse import quote_plus
from TechVJ.util.file_properties import get_name, get_hash, get_media_file_size

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)
lock = asyncio.Lock()

# Global dictionaries for state management
# WARNING: These are in-memory and will be lost on restart.
# Consider using a database (like Redis) for persistent state.
FRESH = {}
SPELL_CHECK = {}

# --- Helper Functions for Refactoring ---

async def edit_menu_helper(query: CallbackQuery, text: str, reply_markup: InlineKeyboardMarkup, photo: str = None):
    """
    Helper function to edit a message with new text, markup, and optionally a new photo.
    This reduces repetition in the main callback handler.
    """
    try:
        if photo:
            await query.client.edit_message_media(
                query.message.chat.id,
                query.message.id,
                InputMediaPhoto(random.choice(PICS) if photo == "random" else photo)
            )
        await query.message.edit_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML,
            disable_web_page_preview=True
        )
    except MessageNotModified:
        pass  # Ignore if the message is already the same
    except Exception as e:
        logger.exception(f"Error in edit_menu_helper: {e}")

def get_settings_buttons(settings: dict, grp_id: str) -> list:
    """
    Generates the list of buttons for the settings menu.
    This function is used by opnsetgrp, opnsetpm, and setgs to avoid code duplication.
    """
    grp_id_str = str(grp_id)
    # Use .get() to provide default values and prevent KeyErrors
    buttons = [
        [
            InlineKeyboardButton('Rᴇsᴜʟᴛ Pᴀɢᴇ', callback_data=f'setgs#button#{settings.get("button", True)}#{grp_id_str}'),
            InlineKeyboardButton('Bᴜᴛᴛᴏn' if settings.get("button", True) else 'Tᴇxᴛ', callback_data=f'setgs#button#{settings.get("button", True)}#{grp_id_str}')
        ],
        [
            InlineKeyboardButton('Pʀᴏᴛᴇᴄᴛ Cᴏɴᴛᴇɴᴛ', callback_data=f'setgs#file_secure#{settings.get("file_secure", False)}#{grp_id_str}'),
            InlineKeyboardButton('✔ Oɴ' if settings.get("file_secure", False) else '✘ Oғғ', callback_data=f'setgs#file_secure#{settings.get("file_secure", False)}#{grp_id_str}')
        ],
        [
            InlineKeyboardButton('Iᴍᴅʙ', callback_data=f'setgs#imdb#{settings.get("imdb", True)}#{grp_id_str}'),
            InlineKeyboardButton('✔ Oɴ' if settings.get("imdb", True) else '✘ Oғғ', callback_data=f'setgs#imdb#{settings.get("imdb", True)}#{grp_id_str}')
        ],
        [
            InlineKeyboardButton('Sᴘᴇʟʟ Cʜᴇᴄᴋ', callback_data=f'setgs#spell_check#{settings.get("spell_check", True)}#{grp_id_str}'),
            InlineKeyboardButton('✔ Oɴ' if settings.get("spell_check", True) else '✘ Oғғ', callback_data=f'setgs#spell_check#{settings.get("spell_check", True)}#{grp_id_str}')
        ],
        [
            InlineKeyboardButton('Wᴇʟᴄᴏᴍᴇ Msɢ', callback_data=f'setgs#welcome#{settings.get("welcome", True)}#{grp_id_str}'),
            InlineKeyboardButton('✔ Oɴ' if settings.get("welcome", True) else '✘ Oғғ', callback_data=f'setgs#welcome#{settings.get("welcome", True)}#{grp_id_str}')
        ],
        [
            InlineKeyboardButton('Aᴜᴛᴏ-Dᴇʟᴇᴛᴇ', callback_data=f'setgs#auto_delete#{settings.get("auto_delete", False)}#{grp_id_str}'),
            InlineKeyboardButton('30 Mɪɴs' if settings.get("auto_delete", False) else '✘ Oғғ', callback_data=f'setgs#auto_delete#{settings.get("auto_delete", False)}#{grp_id_str}')
        ],
        [
            InlineKeyboardButton('Aᴜᴛᴏ-Fɪʟᴛᴇʀ', callback_data=f'setgs#auto_ffilter#{settings.get("auto_ffilter", True)}#{grp_id_str}'),
            InlineKeyboardButton('✔ Oɴ' if settings.get("auto_ffilter", True) else '✘ Oғғ', callback_data=f'setgs#auto_ffilter#{settings.get("auto_ffilter", True)}#{grp_id_str}')
        ],
        [
            InlineKeyboardButton('Mᴀx Bᴜᴛᴛᴏɴs', callback_data=f'setgs#max_btn#{settings.get("max_btn", True)}#{grp_id_str}'),
            InlineKeyboardButton('10' if settings.get("max_btn", True) else f'{MAX_B_TN}', callback_data=f'setgs#max_btn#{settings.get("max_btn", True)}#{grp_id_str}')
        ],
        [
            InlineKeyboardButton('SʜᴏʀᴛLɪɴᴋ', callback_data=f'setgs#is_shortlink#{settings.get("is_shortlink", False)}#{grp_id_str}'),
            InlineKeyboardButton('✔ Oɴ' if settings.get("is_shortlink", False) else '✘ Oғғ', callback_data=f'setgs#is_shortlink#{settings.get("is_shortlink", False)}#{grp_id_str}')
        ]
    ]
    return buttons

async def get_stats_text() -> str:
    """
    Fetches database statistics and formats them into a text string.
    Used by 'stats' and 'rfrsh' callbacks.
    """
    total_users = await db.total_users_count()
    totl_chats = await db.total_chat_count()
    filesp = col.count_documents({})
    totalsec = sec_col.count_documents({})
    
    try:
        stats = vjdb.command('dbStats')
        used_dbSize = (stats['dataSize'] + stats['indexSize']) / (1024 * 1024)
        free_dbSize = 512 - used_dbSize  # Assuming 512MB total
    except Exception:
        used_dbSize, free_dbSize = 0, 0

    try:
        stats2 = sec_db.command('dbStats')
        used_dbSize2 = (stats2['dataSize'] + stats2['indexSize']) / (1024 * 1024)
        free_dbSize2 = 512 - used_dbSize2
    except Exception:
        used_dbSize2, free_dbSize2 = 0, 0

    try:
        stats3 = mydb.command('dbStats')
        used_dbSize3 = (stats3['dataSize'] + stats3['indexSize']) / (1024 * 1024)
        free_dbSize3 = 512 - used_dbSize3
    except Exception:
        used_dbSize3, free_dbSize3 = 0, 0

    return script.STATUS_TXT.format(
        (int(filesp) + int(totalsec)),
        total_users,
        totl_chats,
        filesp,
        round(used_dbSize, 2),
        round(free_dbSize, 2),
        totalsec,
        round(used_dbSize2, 2),
        round(free_dbSize2, 2),
        round(used_dbSize3, 2),
        round(free_dbSize3, 2)
    )

# --- Message Handlers ---

@Client.on_message(filters.group & filters.text & filters.incoming)
async def give_filter(client, message):
    if message.chat.id == SUPPORT_CHAT_ID:
        # Logic for support group
        search = message.text
        temp_files, temp_offset, total_results = await get_search_results(chat_id=message.chat.id, query=search.lower(), offset=0, filter=True)
        if total_results > 0:
            await message.reply_text(f"<b>Hᴇʏ {message.from_user.mention}, {str(total_results)} ʀᴇsᴜʟᴛs ᴀʀᴇ ғᴏᴜɴᴅ ɪɴ ᴍʏ ᴅᴀᴛᴀʙᴀsᴇ ғᴏʀ ʏᴏᴜʀ ᴏ̨ᴜᴇʀʏ {search}. \n\nTʜɪs ɪs ᴀ sᴜᴘᴘᴏʀᴛ ɢʀᴏᴜᴘ sᴏ ᴛʜᴀᴛ ʏᴏᴜ ᴄᴀɴ'ᴛ ɢᴇᴛ ғɪʟᴇs ғʀᴏᴍ ʜᴇʀᴇ...\n\nJᴏɪɴ ᴀɴᴅ Sᴇᴀʀᴄʜ Hᴇʀᴇ - {GRP_LNK}</b>")
        return

    # Main filter logic for other groups
    settings = await get_settings(message.chat.id)
    chatid = message.chat.id 
    user_id = message.from_user.id if message.from_user else 0

    # Force Subscribe Check
    fsub_channel = settings.get('fsub')
    if fsub_channel:
        try:
            btn = await pub_is_subscribed(client, message, fsub_channel)
            if btn:
                btn.append([InlineKeyboardButton("Unmute Me 🔕", callback_data=f"unmuteme#{int(user_id)}")])
                await client.restrict_chat_member(chatid, message.from_user.id, ChatPermissions(can_send_messages=False))
                await message.reply_photo(
                    photo=random.choice(PICS), 
                    caption=f"👋 Hello {message.from_user.mention},\n\nPlease join the channel then click on unmute me button. 😇", 
                    reply_markup=InlineKeyboardMarkup(btn), 
                    parse_mode=enums.ParseMode.HTML
                )
                return
        except Exception as e:
            print(f"Error during fsub check: {e}")
            
    # Filter processing chain
    
    # 1. Global Filters
    global_handled = await global_filters(client, message)
    
    # 2. Manual Filters (if not handled by global)
    if not global_handled:
        manual_handled = await manual_filters(client, message)
        
        # 3. Auto Filter (if not handled by manual)
        if not manual_handled:
            # Cleaned up the KeyError logic
            if settings.get('auto_ffilter') is None:
                await save_group_settings(message.chat.id, 'auto_ffilter', True)
                settings['auto_ffilter'] = True # Update local copy
            
            if settings['auto_ffilter']:
                ai_search = True
                reply_msg = await message.reply_text(f"<b><i>Searching For {message.text} 🔍</i></b>")
                await auto_filter(client, message.text, message, reply_msg, ai_search)

@Client.on_message(filters.private & filters.text & filters.incoming)
async def pm_text(bot, message):
    content = message.text
    if content.startswith("/") or content.startswith("#"): 
        return  # ignore commands and hashtags
    
    if PM_SEARCH:
        ai_search = True
        reply_msg = await bot.send_message(
            message.from_user.id, 
            f"<b><i>Searching For {content} 🔍</i></b>", 
            reply_to_message_id=message.id
        )
        await auto_filter(bot, content, message, reply_msg, ai_search)
    
@Client.on_callback_query(filters.regex(r"^next"))
async def next_page(bot, query):
    # This function is now effectively disabled by the "single page" request,
    # as no "next" buttons will be generated by auto_filter.
    # We leave it here in case the user changes their mind.
    ident, req, key, offset_str = query.data.split("_")
    
    if int(req) not in [query.from_user.id, 0]:
        return await query.answer(script.ALRT_TXT.format(query.from_user.first_name), show_alert=True)

    try:
        offset = int(offset_str)
    except:
        offset = 0

    search = FRESH.get(key)
    if not search:
        # BUG FIX: Handle cases where bot restarts and FRESH is empty
        return await query.answer(script.OLD_ALRT_TXT.format(query.from_user.first_name), show_alert=True)
    
    curr_time = datetime.now(pytz.timezone('Asia/Kolkata')).time()
    
    settings = await get_settings(query.message.chat.id)
    # Use the same limit logic as auto_filter
    limit = 100 if settings.get("button", True) else 60
    
    files, n_offset, total = await get_search_results(query.message.chat.id, search, offset=offset, filter=True, limit=limit)
    
    if not files:
        return await query.answer("No more files found.", show_alert=True)

    n_offset = int(n_offset) if n_offset else 0

    temp.GETALL[key] = files
    temp.SHORT[query.from_user.id] = query.message.chat.id
    pre = 'filep' if settings.get('file_secure', False) else 'file'

    if settings.get("button", True):
        btn = [
            [
                InlineKeyboardButton(
                    text=f"[{get_size(file['file_size'])}] {' '.join(filter(lambda x: not x.startswith('[') and not x.startswith('@') and not x.startswith('www.'), file['file_name'].split()))}", 
                    callback_data=f'{pre}#{file["file_id"]}'
                ),
            ]
            for file in files
        ]
        btn.insert(0, [InlineKeyboardButton("•  Bᴀᴄᴋ Uᴘ CʜᴀNNᴇʟ  •", url="https://t.me/KR_PICTURE")])
    else:
        btn = [[InlineKeyboardButton("•  Bᴀᴄᴋ Uᴘ CʜᴀNNᴇʟ  •", url="https://t.me/KR_PICTURE")]]

    # Simplified pagination logic (from before "single page" request)
    page_size = 10 if settings.get('max_btn', True) else int(MAX_B_TN)
    
    if 0 < offset <= page_size:
        off_set = 0
    elif offset == 0:
        off_set = None
    else:
        off_set = offset - page_size

    page_num = math.ceil(int(offset) / page_size) + 1
    total_pages = math.ceil(total / page_size)
    
    pagination_buttons = []
    if off_set is not None:
        pagination_buttons.append(InlineKeyboardButton("⌫ 𝐁𝐀𝐂𝐊", callback_data=f"next_{req}_{key}_{off_set}"))
    
    pagination_buttons.append(InlineKeyboardButton(f"{page_num} / {total_pages}", callback_data="pages"))
    
    if n_offset != 0:
        pagination_buttons.append(InlineKeyboardButton("𝐍𝐄𝐗𝐓 ➪", callback_data=f"next_{req}_{key}_{n_offset}"))

    btn.append(pagination_buttons)

    if not settings.get("button", True):
        cur_time = datetime.now(pytz.timezone('Asia/Kolkata')).time()
        time_difference = timedelta(hours=cur_time.hour, minutes=cur_time.minute, seconds=(cur_time.second+(cur_time.microsecond/1000000))) - timedelta(hours=curr_time.hour, minutes=curr_time.minute, seconds=(curr_time.second+(curr_time.microsecond/1000000)))
        remaining_seconds = "{:.2f}".format(time_difference.total_seconds())
        cap = await get_cap(settings, remaining_seconds, files, query, total, search)
        try:
            await query.message.edit_text(text=cap, reply_markup=InlineKeyboardMarkup(btn), disable_web_page_preview=True)
        except MessageNotModified:
            pass
    else:
        try:
            await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(btn))
        except MessageNotModified:
            pass
            
    await query.answer()

@Client.on_callback_query(filters.regex(r"^spol"))
async def advantage_spoll_choker(bot, query):
    _, user, movie_idx = query.data.split('#')

    if int(user) != 0 and query.from_user.id != int(user):
        return await query.answer(script.ALRT_TXT.format(query.from_user.first_name), show_alert=True)

    if movie_idx == "close_spellcheck":
        return await query.message.delete()

    movies = SPELL_CHECK.get(query.message.reply_to_message.id)
    if not movies:
        # BUG FIX: Handle cases where bot restarts and SPELL_CHECK is empty
        return await query.answer(script.OLD_ALRT_TXT.format(query.from_user.first_name), show_alert=True)

    try:
        movie = movies[int(movie_idx)]
    except IndexError:
        return await query.answer("Invalid selection.", show_alert=True)

    movie = re.sub(r"[:\-]", " ", movie)
    movie = re.sub(r"\s+", " ", movie).strip()
    
    await query.answer(script.TOP_ALRT_MSG)
    reply_msg = await query.message.edit_text(f"<b><i>Searching For {movie} 🔍</i></b>")
    
    # Same filter chain as `give_filter`
    gl = await global_filters(bot, query.message, text=movie)
    if gl == False:
        k = await manual_filters(bot, query.message, text=movie)
        if k == False:
            
            # --- MODIFICATION: Set limit based on button/text mode ---
            settings = await get_settings(query.message.chat.id)
            limit = 100 if settings.get("button", True) else 60
            
            files, offset, total_results = await get_search_results(query.message.chat.id, movie, offset=0, filter=True, limit=limit)
            # --- END MODIFICATION ---

            if files:
                spoll_data = (movie, files, offset, total_results)
                ai_search = True # Not used by spoll path, but good to set
                await auto_filter(bot, movie, query, reply_msg, ai_search, spoll=spoll_data)
            else:
                reqstr1 = query.from_user.id if query.from_user else 0
                reqstr = await bot.get_users(reqstr1)
                if NO_RESULTS_MSG:
                    await bot.send_message(chat_id=LOG_CHANNEL, text=(script.NORSLTS.format(reqstr.id, reqstr.mention, movie)))
                
                # Deleting "Searching..." message if no results
                try:
                    await query.message.delete()
                except:
                    pass
                return
                
@Client.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    data = query.data
    
    if data == "close_data":
        await query.message.delete()
        
    elif data == "get_trail":
        user_id = query.from_user.id
        free_trial_status = await db.get_free_trial_status(user_id)
        if not free_trial_status:            
            await db.give_free_trail(user_id)
            new_text = "**ʏᴏᴜ ᴄᴀɴ ᴜsᴇ ꜰʀᴇᴇ ᴛʀᴀɪʟ ꜰᴏʀ 5 ᴍɪɴᴜᴛᴇs ꜰʀᴏᴍ ɴᴏᴡ 😀\n\nआप अब से 5 मिनट के लिए निःशुल्क ट्रायल का उपयोग कर सकते हैं 😀**"        
            await query.message.edit_text(text=new_text)
        else:
            new_text= "**🤣 you already used free now no more free trail. please buy subscription here are our 👉 /plans**"
            await query.message.edit_text(text=new_text)
            
    elif data == "buy_premium":
        btn = [[InlineKeyboardButton("✅sᴇɴᴅ ʏᴏᴜʀ ᴘᴀʏᴍᴇɴᴛ ʀᴇᴄᴇɪᴘᴛ ʜᴇʀᴇ ✅", url = OWNER_LINK)]]
        btn.append([InlineKeyboardButton("⚠️ᴄʟᴏsᴇ / ᴅᴇʟᴇᴛᴇ⚠️", callback_data="close_data")])
        reply_markup = InlineKeyboardMarkup(btn)
        await query.message.reply_photo(
            photo=PAYMENT_QR,
            caption=PAYMENT_TEXT,
            reply_markup=reply_markup
        )
        
    elif data == "gfiltersdeleteallconfirm":
        await del_allg(query.message, 'gfilters')
        await query.answer("Done !", show_alert=True)
        
    elif data == "gfiltersdeleteallcancel": 
        await query.message.reply_to_message.delete()
        await query.message.delete()
        await query.answer("Process Cancelled !", show_alert=True)
        
    elif data == "delallconfirm":
        userid = query.from_user.id
        chat_type = query.message.chat.type
        grp_id = None
        title = None

        if chat_type == enums.ChatType.PRIVATE:
            grpid = await active_connection(str(userid))
            if grpid is not None:
                grp_id = grpid
                try:
                    chat = await client.get_chat(grpid)
                    title = chat.title
                except:
                    await query.message.edit_text("Mᴀᴋᴇ sᴜʀᴇ I'ᴍ ᴘʀᴇsᴇɴᴛ ɪɴ ʏᴏᴜʀ ɢʀᴏᴜᴘ!!", quote=True)
                    return await query.answer()
            else:
                await query.message.edit_text(
                    "I'ᴍ ɴᴏᴛ ᴄᴏɴɴᴇᴄᴛED ᴛᴏ ᴀɴʏ ɢʀᴏᴜᴘs!\nCʜᴇᴄᴋ /connections ᴏʀ ᴄᴏɴɴᴇᴄᴛ ᴛᴏ ᴀɴʏ ɢʀᴏᴜᴘs",
                    quote=True
                )
                return await query.answer()

        elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
            grp_id = query.message.chat.id
            title = query.message.chat.title
        else:
            return await query.answer()

        if grp_id:
            st = await client.get_chat_member(grp_id, userid)
            if (st.status == enums.ChatMemberStatus.OWNER) or (str(userid) in ADMINS):
                await del_all(query.message, grp_id, title)
            else:
                await query.answer("Yᴏᴜ ɴᴇᴇᴅ ᴛᴏ ʙᴇ Gʀᴏᴜᴘ Oᴡɴᴇʀ ᴏʀ ᴀɴ Aᴜᴛʜ Usᴇʀ ᴛᴏ ᴅᴏ ᴛʜᴀᴛ!", show_alert=True)
        
    elif data == "delallcancel":
        userid = query.from_user.id
        chat_type = query.message.chat.type

        if chat_type == enums.ChatType.PRIVATE:
            await query.message.reply_to_message.delete()
            await query.message.delete()

        elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
            st = await client.get_chat_member(query.message.chat.id, userid)
            if (st.status == enums.ChatMemberStatus.OWNER) or (str(userid) in ADMINS):
                await query.message.delete()
                try:
                    await query.message.reply_to_message.delete()
                except:
                    pass
            else:
                await query.answer("Tʜᴀᴛ's ɴᴏᴛ ғᴏʀ ʏᴏᴜ!!", show_alert=True)
                
    elif data.startswith("groupcb"):
        await query.answer()
        group_id = data.split(":")[1]
        act = data.split(":")[2]
        
        try:
            hr = await client.get_chat(int(group_id))
            title = hr.title
        except Exception:
            await query.message.edit_text("Error: Could not get chat info. Maybe I was kicked?")
            return

        stat = "DISCONNECT" if act else "CONNECT"
        cb = "disconnect" if act else "connectcb"

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{stat}", callback_data=f"{cb}:{group_id}"),
             InlineKeyboardButton("DELETE", callback_data=f"deletecb:{group_id}")],
            [InlineKeyboardButton("BACK", callback_data="backcb")]
        ])
        await query.message.edit_text(
            f"Gʀᴏᴜᴘ Nᴀᴍᴇ : **{title}**\nGʀᴏᴜᴘ ID : `{group_id}`",
            reply_markup=keyboard,
            parse_mode=enums.ParseMode.MARKDOWN
        )
        
    elif data.startswith("connectcb"):
        await query.answer()
        group_id = data.split(":")[1]
        try:
            hr = await client.get_chat(int(group_id))
            title = hr.title
        except Exception:
            await query.message.edit_text("Error: Could not get chat info. Maybe I was kicked?")
            return
        
        user_id = query.from_user.id
        mkact = await make_active(str(user_id), str(group_id))

        if mkact:
            await query.message.edit_text(
                f"Cᴏɴɴᴇᴄᴛᴇᴅ ᴛᴏ **{title}**",
                parse_mode=enums.ParseMode.MARKDOWN
            )
        else:
            await query.message.edit_text('Sᴏᴍᴇ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ!!', parse_mode=enums.ParseMode.MARKDOWN)
            
    elif data.startswith("disconnect"):
        await query.answer()
        group_id = data.split(":")[1]
        try:
            hr = await client.get_chat(int(group_id))
            title = hr.title
        except Exception:
            title = "this group (info unavailable)"

        user_id = query.from_user.id
        mkinact = await make_inactive(str(user_id))

        if mkinact:
            await query.message.edit_text(
                f"Dɪsᴄᴏɴɴᴇᴄᴛᴇᴅ ғʀᴏᴍ **{title}**",
                parse_mode=enums.ParseMode.MARKDOWN
            )
        else:
            await query.message.edit_text(
                f"Sᴏᴍᴇ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ!!",
                parse_mode=enums.ParseMode.MARKDOWN
            )
            
    elif data.startswith("deletecb"):
        await query.answer()
        user_id = query.from_user.id
        group_id = data.split(":")[1]
        delcon = await delete_connection(str(user_id), str(group_id))

        if delcon:
            await query.message.edit_text("Sᴜᴄᴄᴇssғᴜʟʟʏ ᴅᴇʟᴇᴛᴇᴅ ᴄᴏɴɴᴇᴄᴛɪᴏɴ !")
        else:
            await query.message.edit_text(
                f"Sᴏᴍᴇ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ!!",
                parse_mode=enums.ParseMode.MARKDOWN
            )
            
    elif data == "backcb":
        await query.answer()
        userid = query.from_user.id
        groupids = await all_connections(str(userid))
        
        if not groupids:
            await query.message.edit_text(
                "Tʜᴇʀᴇ ᴀʀᴇ ɴᴏ ᴀᴄᴛɪᴠᴇ ᴄᴏɴɴᴇᴄᴛɪᴏns!! Cᴏɴɴᴇᴄᴛ ᴛᴏ sᴏᴍᴇ ɢʀᴏᴜᴘs ғɪʀsᴛ.",
            )
            return

        buttons = []
        for groupid in groupids:
            try:
                ttl = await client.get_chat(int(groupid))
                title = ttl.title
                active = await if_active(str(userid), str(groupid))
                act = " - ACTIVE" if active else ""
                buttons.append(
                    [InlineKeyboardButton(text=f"{title}{act}", callback_data=f"groupcb:{groupid}:{act}")]
                )
            except:
                pass # Skip if bot was kicked
                
        if buttons:
            await query.message.edit_text(
                "Yᴏᴜʀ ᴄᴏɴɴᴇᴄᴛᴇᴅ ɢʀᴏᴜᴘ ᴅᴇᴛᴀɪʟs ;\n\n",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        else:
            await query.message.edit_text("You have no valid connections.")

    elif data.startswith("gfilteralert"):
        try:
            _, i, keyword = data.split(":", 2)
            reply_text, btn, alerts, fileid = await find_gfilter('gfilters', keyword)
            if alerts:
                alerts_list = ast.literal_eval(alerts)
                alert = alerts_list[int(i)]
                alert = alert.replace("\\n", "\n").replace("\\t", "\t")
                await query.answer(alert, show_alert=True)
        except Exception as e:
            logger.error(f"Error in gfilteralert: {e}")
            await query.answer("Error: Could not retrieve alert.", show_alert=True)
    
    elif data.startswith("alertmessage"):
        try:
            grp_id = query.message.chat.id
            _, i, keyword = data.split(":", 2)
            reply_text, btn, alerts, fileid = await find_filter(grp_id, keyword)
            if alerts:
                alerts_list = ast.literal_eval(alerts)
                alert = alerts_list[int(i)]
                alert = alert.replace("\\n", "\n").replace("\\t", "\t")
                await query.answer(alert, show_alert=True)
        except Exception as e:
            logger.error(f"Error in alertmessage: {e}")
            await query.answer("Error: Could not retrieve alert.", show_alert=True)
        
    elif data.startswith("file"):
        clicked = query.from_user.id
        try:
            typed = query.message.reply_to_message.from_user.id
        except:
            typed = query.from_user.id # If not a reply, assume opener is typer

        if clicked != typed:
             return await query.answer(f"Hᴇʏ {query.from_user.first_name}, Tʜɪs Is Nᴏᴛ Yᴏᴜʀ Mᴏᴠɪᴇ Rᴇǫᴜᴇsᴛ. Rᴇǫᴜᴇsᴛ Yᴏᴜʀ's !", show_alert=True)

        ident, file_id = data.split("#")
        files_ = await get_file_details(file_id)
        if not files_:
            return await query.answer('Nᴏ sᴜᴄʜ ғɪʟᴇ ᴇxɪsᴛ.', show_alert=True)

        settings = await get_settings(query.message.chat.id)
        
        try:
            if settings.get('is_shortlink', False) and not await db.has_premium_access(query.from_user.id):
                temp.SHORT[clicked] = query.message.chat.id
                await query.answer(url=f"https://telegram.me/{temp.U_NAME}?start=short_{file_id}")
            else:
                # Premium users or shortlink disabled
                await query.answer(url=f"https://telegram.me/{temp.U_NAME}?start={ident}_{file_id}")
        except UserIsBlocked:
            await query.answer('Uɴʙʟᴏᴄᴋ ᴛʜᴇ ʙᴏᴛ ᴍᴀʜɴ !', show_alert=True)
        except PeerIdInvalid:
            await query.answer(url=f"https://telegram.me/{temp.U_NAME}?start={ident}_{file_id}")
        except Exception as e:
            logger.error(f"Error in file handler: {e}")
            await query.answer(url=f"https://telegram.me/{temp.U_NAME}?start={ident}_{file_id}")
            
    elif data.startswith("sendfiles"):
        ident, key = data.split("#")
        settings = await get_settings(query.message.chat.id)
        pre = 'allfilesp' if settings.get('file_secure', False) else 'allfiles'
        
        try:
            if settings.get('is_shortlink', False) and not await db.has_premium_access(query.from_user.id):
                await query.answer(url=f"https://telegram.me/{temp.U_NAME}?start=sendfiles1_{key}")
            else:
                await query.answer(url=f"https://telegram.me/{temp.U_NAME}?start={pre}_{key}")
        except UserIsBlocked:
            await query.answer('Uɴʙʟᴏᴄᴋ ᴛʜᴇ ʙᴏᴛ ᴍᴀʜɴ !', show_alert=True)
        except PeerIdInvalid:
            await query.answer(url=f"https://telegram.me/{temp.U_NAME}?start={pre}_{key}") # Fallback
        except Exception as e:
            logger.exception(e)
            await query.answer(url=f"https://telegram.me/{temp.U_NAME}?start={pre}_{key}") # Fallback

    elif data.startswith("unmuteme"):
        _, userid_str = data.split("#")
        user_id = query.from_user.id
        
        if user_id != int(userid_str):
             return await query.answer("Not For Your My Dear", show_alert=True)

        settings = await get_settings(int(query.message.chat.id))
        fsub_channel = settings.get('fsub')
        
        if not fsub_channel:
            return await query.answer("ForceSubscribe is not enabled here.", show_alert=True)
            
        try:
            btn = await pub_is_subscribed(client, query, fsub_channel)
            if btn:
                await query.answer("Kindly Join Given Channel Then Click On Unmute Button", show_alert=True)
            else:
                await client.unban_chat_member(query.message.chat.id, user_id)
                await query.answer("Unmuted Successfully !", show_alert=True)
                await query.message.delete()
        except Exception as e:
            logger.error(f"Error in unmuteme: {e}")
            await query.answer("An error occurred. Maybe I'm not an admin?", show_alert=True)
   
    elif data.startswith("del"):
        # This handler seems redundant, it just generates a 'file_' start link
        # which is what the 'file' handler does.
        ident, file_id = data.split("#")
        await query.answer(url=f"https://telegram.me/{temp.U_NAME}?start=file_{file_id}")
    
    elif data.startswith("checksub"):
        if AUTH_CHANNEL and not await is_subscribed(client, query):
            await query.answer("Jᴏɪɴ ᴏᴜʀ Bᴀᴄᴋ-ᴜᴘ ᴄʜᴀɴɴᴇʟ ᴍᴀʜɴ! 😒", show_alert=True)
            return
        ident, kk, file_id = data.split("#")
        await query.answer(url=f"https://t.me/{temp.U_NAME}?start={kk}_{file_id}")
    
    elif data == "pages":
        await query.answer()
    
    elif data.startswith("killfilesdq"):
        _, keyword = data.split("#")
        files, total = await get_bad_files(keyword)
        if not files:
            return await query.message.edit_text(f"<b>No files found to delete for query: {keyword}</b>")

        await query.message.edit_text(f"<b>Found {total} files for query {keyword}. File deletion process will start in 5 seconds !</b>")
        await asyncio.sleep(5)
        
        deleted = 0
        async with lock:
            try:
                for file in files:
                    file_id = file["file_id"]
                    file_name = file["file_name"]
                    
                    result = col.delete_one({'file_id': file_id})
                    if not result.deleted_count:
                        result = sec_col.delete_one({'file_id': file_id})
                    
                    if result.deleted_count:
                        logger.info(f'Successfully deleted {file_name} from database.')
                        deleted += 1
                        
                    if deleted % 50 == 0:
                        await query.message.edit_text(f"<b>Process started... Successfully deleted {deleted} / {total} files for your query {keyword} !\n\nPlease wait...</b>")
            except Exception as e:
                logger.exception(e)
                await query.message.edit_text(f'Error: {e}')
            else:
                await query.message.edit_text(f"<b>Process Completed!\n\nSuccessfully deleted {deleted} files from database for your query {keyword}.</b>")
    
    # --- Settings Handlers (Refactored) ---
    elif data.startswith("opnsetgrp"):
        _, grp_id = data.split("#")
        userid = query.from_user.id if query.from_user else None
        st = await client.get_chat_member(grp_id, userid)
        if not (st.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER] or str(userid) in ADMINS):
            return await query.answer("Yᴏᴜ Dᴏɴ'ᴛ Hᴀᴠᴇ Tʜᴇ Rɪɢʜᴛs Tᴏ Dᴏ Tʜɪs !", show_alert=True)
        
        title = query.message.chat.title
        settings = await get_settings(grp_id)
        if settings is not None:
            buttons = get_settings_buttons(settings, grp_id)
            reply_markup = InlineKeyboardMarkup(buttons)
            await query.message.edit_text(
                text=f"<b>Cʜᴀɴɢᴇ Yᴏᴜʀ Sᴇᴛᴛɪɴɢs Fᴏʀ {title} As Yᴏᴜʀ Wɪsʜ ⚙</b>",
                disable_web_page_preview=True,
                parse_mode=enums.ParseMode.HTML,
                reply_markup=reply_markup
            )
        else:
            await query.answer("Could not fetch settings for this group.", show_alert=True)
        
    elif data.startswith("opnsetpm"):
        _, grp_id = data.split("#")
        userid = query.from_user.id if query.from_user else None
        st = await client.get_chat_member(grp_id, userid)
        if not (st.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER] or str(userid) in ADMINS):
            return await query.answer("Yᴏᴜ Dᴏɴ'ᴛ Hᴀᴠᴇ Tʜᴇ Rɪɢʜᴛs Tᴏ Dᴏ Tʜɪs !", show_alert=True)

        title = query.message.chat.title
        settings = await get_settings(grp_id)
        if settings is None:
            return await query.answer("Could not fetch settings for this group.", show_alert=True)

        btn2 = [[InlineKeyboardButton("Cʜᴇᴄᴋ PM", url=f"telegram.me/{temp.U_NAME}")]]
        reply_markup = InlineKeyboardMarkup(btn2)
        await query.message.edit_text(f"<b>Yᴏᴜʀ sᴇᴛᴛɪɴɢs ᴍᴇɴᴜ ғᴏʀ {title} ʜᴀs ʙᴇᴇɴ sᴇɴᴛ ᴛᴏ ʏᴏᴜʀ PM</b>", reply_markup=reply_markup)
        
        buttons = get_settings_buttons(settings, grp_id)
        reply_markup = InlineKeyboardMarkup(buttons)
        try:
            await client.send_message(
                chat_id=userid,
                text=f"<b>Cʜᴀɴɢᴇ Yᴏᴜʀ Sᴇᴛᴛɪɴɢs Fᴏʀ {title} As Yᴏᴜʀ Wɪsʜ ⚙</b>",
                reply_markup=reply_markup,
                disable_web_page_preview=True,
                parse_mode=enums.ParseMode.HTML
            )
        except UserIsBlocked:
            await query.answer("I can't send you the menu, you've blocked me!", show_alert=True)
        except Exception as e:
            logger.error(f"Error sending settings to PM: {e}")

    elif data.startswith("setgs"):
        _, set_type, status, grp_id = data.split("#")
        grpid = await active_connection(str(query.from_user.id))

        if str(grp_id) != str(grpid):
            await query.message.edit_text("Yᴏᴜʀ Aᴄᴛɪᴠᴇ Cᴏɴɴᴇᴄᴛɪᴏɴ Hᴀs Bᴇᴇɴ Cʜᴀɴɢᴇᴅ. Gᴏ Tᴏ /connections ᴀɴᴅ ᴄʜᴀɴɢᴇ ʏᴏᴜʀ ᴀᴄᴛɪᴠᴇ ᴄᴏɴɴᴇᴄᴛɪᴏɴ.")
            return await query.answer()

        new_status = False if status == "True" else True
        
        settings = await get_settings(grpid)
        if set_type == "is_shortlink" and new_status and not settings.get('shortlink'):
            return await query.answer(text = "First Add Your Shortlink Url And Api By /shortlink Command, Then Turn Me On.", show_alert = True)
        
        await save_group_settings(grpid, set_type, new_status)
        
        # Refresh settings and update menu
        settings = await get_settings(grpid)
        if settings is not None:
            buttons = get_settings_buttons(settings, grpid)
            reply_markup = InlineKeyboardMarkup(buttons)
            await query.message.edit_reply_markup(reply_markup)
        
    # --- Request Status Handlers ---
    elif data.startswith("show_option"):
        if query.from_user.id not in ADMINS:
            return await query.answer("Yᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ sᴜғғɪᴄɪᴀɴᴛ ʀɪɢʜᴛs ᴛᴏ ᴅᴏ ᴛʜɪs !", show_alert=True)
            
        _, from_user = data.split("#")
        btn = [
            [
                InlineKeyboardButton("Uɴᴀᴠᴀɪʟᴀʙʟᴇ", callback_data=f"unavailable#{from_user}"),
                InlineKeyboardButton("Uᴘʟᴏᴀᴅᴇᴅ", callback_data=f"uploaded#{from_user}")
            ],
            [InlineKeyboardButton("Aʟʀᴇᴀᴅʏ Aᴠᴀɪʟᴀʙʟᴇ", callback_data=f"already_available#{from_user}")]
        ]
        reply_markup = InlineKeyboardMarkup(btn)
        await query.message.edit_reply_markup(reply_markup)
        await query.answer("Hᴇʀᴇ ᴀʀᴇ ᴛʜᴇ ᴏᴘᴛɪᴏɴs !")

    elif data.startswith("unavailable"):
        if query.from_user.id not in ADMINS:
            return await query.answer("Yᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ sᴜғғɪᴄɪᴀɴᴛ ʀɪɢʜᴛs ᴛᴏ ᴅᴏ ᴛʜɪs !", show_alert=True)
        
        _, from_user = data.split("#")
        btn = [[InlineKeyboardButton("⚠️ Uɴᴀᴠᴀɪʟᴀʙʟᴇ ⚠️", callback_data=f"unalert#{from_user}")]]
        reply_markup = InlineKeyboardMarkup(btn)
        
        content = query.message.text
        await query.message.edit_text(f"<b><strike>{content}</strike></b>", reply_markup=reply_markup)
        await query.answer("Sᴇᴛ ᴛᴏ Uɴᴀᴠᴀɪʟᴀʙʟᴇ !")
        
        user = await client.get_users(from_user)
        notify_text = f"<b>Hᴇʏ {user.mention}, Sᴏʀʀʏ Yᴏᴜʀ ʀᴇᴏ̨ᴜᴇsᴛ ɪs ᴜɴᴀᴠᴀɪʟᴀʙʟᴇ. Sᴏ ᴏᴜʀ ᴍᴏᴅᴇʀᴀᴛᴏʀs ᴄᴀɴ'ᴛ ᴜᴘʟᴏᴀᴅ ɪᴛ.</b>"
        btn2 = [[
                 InlineKeyboardButton('Jᴏɪɴ Cʜᴀɴɴᴇʟ', url=link.invite_link),
                 InlineKeyboardButton("Vɪᴇᴡ Sᴛᴀᴛᴜs", url=f"{query.message.link}")
               ]]
        try:
            await client.send_message(chat_id=int(from_user), text=notify_text, reply_markup=InlineKeyboardMarkup(btn2))
        except UserIsBlocked:
            await client.send_message(chat_id=int(SUPPORT_CHAT_ID), text=f"{notify_text}\n\nNᴏᴛᴇ: Tʜɪs ᴍᴇssᴀɢᴇ ɪs sᴇɴᴛ ᴛᴏ ᴛʜɪs ɢʀᴏᴜᴘ ʙᴇᴄᴀᴜsᴇ ʏᴏᴜ'ᴠᴇ ʙʟᴏᴄᴋᴇᴅ ᴛʜᴇ ʙᴏᴛ.", reply_markup=InlineKeyboardMarkup(btn2))

    elif data.startswith("uploaded"):
        if query.from_user.id not in ADMINS:
            return await query.answer("Yᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ sᴜғғɪᴄɪᴀɴᴛ ʀɪɢʜᴛs ᴛᴏ ᴅᴏ ᴛʜɪs !", show_alert=True)

        _, from_user = data.split("#")
        btn = [[InlineKeyboardButton("✅ Uᴘʟᴏᴀᴅᴇᴅ ✅", callback_data=f"upalert#{from_user}")]]
        reply_markup = InlineKeyboardMarkup(btn)
        
        content = query.message.text
        await query.message.edit_text(f"<b><strike>{content}</strike></b>", reply_markup=reply_markup)
        await query.answer("Sᴇᴛ ᴛᴏ Uᴘʟᴏᴀᴅᴇᴅ !")
        
        user = await client.get_users(from_user)
        notify_text = f"<b>Hᴇʏ {user.mention}, Yᴏᴜʀ ʀᴇᴏ̨ᴜᴇsᴛ ʜᴀs ʙᴇᴇɴ ᴜᴘʟᴏᴀᴅᴇᴅ ʙʏ ᴏᴜʀ ᴍᴏᴅᴇʀᴀᴛᴏʀs. Kɪɴᴅʟʏ sᴇᴀʀᴄʜ ɪɴ ᴏᴜʀ Gʀᴏᴜᴘ.</b>"
        btn2 = [[
                 InlineKeyboardButton('Jᴏɪɴ Cʜᴀɴɴᴇʟ', url=link.invite_link),
                 InlineKeyboardButton("Vɪᴇᴡ Sᴛᴀᴛᴜs", url=f"{query.message.link}")
               ],[
                 InlineKeyboardButton("Rᴇᴏ̨ᴜᴇsᴛ Gʀᴏᴜᴘ Lɪɴᴋ", url="https://t.me/Sandalwood_Kannada_Group")
               ]]
        try:
            await client.send_message(chat_id=int(from_user), text=notify_text, reply_markup=InlineKeyboardMarkup(btn2))
        except UserIsBlocked:
            await client.send_message(chat_id=int(SUPPORT_CHAT_ID), text=f"{notify_text}\n\nNᴏᴛᴇ: Tʜɪs ᴍᴇssᴀɢᴇ ɪs sᴇɴᴛ ᴛᴏ ᴛʜɪs ɢʀᴏᴜᴘ ʙᴇᴄᴀᴜsᴇ ʏᴏᴜ'ᴠᴇ ʙʟᴏᴄᴋᴇᴅ ᴛʜᴇ ʙᴏᴛ.", reply_markup=InlineKeyboardMarkup(btn2))

    elif data.startswith("already_available"):
        if query.from_user.id not in ADMINS:
            return await query.answer("Yᴏᴜ ᴅᴏɴ'ᴛ ʜᴀᴠᴇ sᴜғғɪᴄɪᴀɴᴛ ʀɪɢʜᴛs ᴛᴏ ᴅᴏ ᴛʜɪs !", show_alert=True)

        _, from_user = data.split("#")
        btn = [[InlineKeyboardButton("🟢 Aʟʀᴇᴀᴅʏ Aᴠᴀɪʟᴀʙʟᴇ 🟢", callback_data=f"alalert#{from_user}")]]
        reply_markup = InlineKeyboardMarkup(btn)
        
        content = query.message.text
        await query.message.edit_text(f"<b><strike>{content}</strike></b>", reply_markup=reply_markup)
        await query.answer("Sᴇᴛ ᴛᴏ Aʟʀᴇᴀᴅʏ Aᴠᴀɪʟᴀʙʟᴇ !")
        
        user = await client.get_users(from_user)
        notify_text = f"<b>Hᴇʏ {user.mention}, Yᴏᴜʀ ʀᴇᴏ̨ᴜᴇsᴛ ɪs ᴀʟʀᴇᴀᴅʏ ᴀᴠᴀɪʟᴀʙʟᴇ ᴏɴ ᴏᴜʀ ʙᴏᴛ's ᴅᴀᴛᴀʙᴀsᴇ. Kɪɴᴅʟʏ sᴇᴀʀᴄʜ ɪɴ ᴏᴜʀ Gʀᴏᴜᴘ.</b>"
        btn2 = [[
                 InlineKeyboardButton('Jᴏɪɴ Cʜᴀɴɴᴇʟ', url=link.invite_link),
                 InlineKeyboardButton("Vɪᴇᴡ Sᴛᴀᴛᴜs", url=f"{query.message.link}")
               ],[
                 InlineKeyboardButton("Rᴇᴏ̨ᴜᴇsᴛ Gʀᴏᴜᴘ Lɪɴᴋ", url="https://t.me/Sandalwood_Kannada_Group")
               ]]
        try:
            await client.send_message(chat_id=int(from_user), text=notify_text, reply_markup=InlineKeyboardMarkup(btn2))
        except UserIsBlocked:
            await client.send_message(chat_id=int(SUPPORT_CHAT_ID), text=f"{notify_text}\n\nNᴏᴛᴇ: Tʜɪs ᴍᴇssᴀɢᴇ ɪs sᴇɴᴛ ᴛᴏ ᴛʜɪs ɢʀᴏᴜᴘ ʙᴇᴄᴀᴜsᴇ ʏᴏᴜ'ᴠᴇ ʙʟᴏᴄᴋᴇᴅ ᴛʜᴇ ʙᴏᴛ.", reply_markup=InlineKeyboardMarkup(btn2))

    elif data.startswith("alalert"):
        _, from_user = data.split("#")
        if int(query.from_user.id) == int(from_user):
            await query.answer(f"Hᴇʏ {query.from_user.first_name}, Yᴏᴜʀ Rᴇᴏ̨ᴜᴇsᴛ ɪs Aʟʀᴇᴀᴅʏ Aᴠᴀɪʟᴀʙʟᴇ !", show_alert=True)
        else:
            await query.answer("This alert is not for you.", show_alert=True)

    elif data.startswith("upalert"):
        _, from_user = data.split("#")
        if int(query.from_user.id) == int(from_user):
            await query.answer(f"Hᴇʏ {query.from_user.first_name}, Yᴏᴜʀ Rᴇᴏ̨ᴜᴇsᴛ ɪs Uᴘʟᴏᴀᴅᴇᴅ !", show_alert=True)
        else:
            await query.answer("This alert is not for you.", show_alert=True)
        
    elif data.startswith("unalert"):
        _, from_user = data.split("#")
        if int(query.from_user.id) == int(from_user):
            await query.answer(f"Hᴇʏ {query.from_user.first_name}, Yᴏᴜʀ Rᴇᴏ̨ᴜᴇsᴛ ɪs Uɴᴀᴠᴀɪʟᴀʙʟᴇ !", show_alert=True)
        else:
            await query.answer("This alert is not for you.", show_alert=True)

    # --- Static Menu Handlers (Refactored) ---
    
    elif data == "start":
        buttons = [[
            InlineKeyboardButton('⤬ ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘ ⤬', url=f'http://t.me/{temp.U_NAME}?startgroup=true')
        ],[
            InlineKeyboardButton('ᴇᴀʀɴ ᴍᴏɴᴇʏ', callback_data="shortlink_info"),
            InlineKeyboardButton('ᴍᴏᴠɪᴇ ɢʀᴏᴜᴘ', url=GRP_LNK)
        ],[
            InlineKeyboardButton('ʜᴇʟᴘ', callback_data='help'),
            InlineKeyboardButton('ᴀʙᴏᴜᴛ', callback_data='about')
        ]]
        if PREMIUM_AND_REFERAL_MODE:
            buttons.append([InlineKeyboardButton('ᴘʀᴇᴍɪᴜᴍ ᴀɴᴅ ʀᴇғᴇʀʀᴀʟ', callback_data='subscription')])
        buttons.append([InlineKeyboardButton('ᴊᴏɪɴ ᴜᴘᴅᴀᴛᴇ ᴄʜᴀɴɴᴇʟ', url=CHNL_LNK)])
        if CLONE_MODE:
            buttons.append([InlineKeyboardButton('ᴄʀᴇᴀᴛᴇ ᴏᴡɴ ᴄʟᴏɴᴇ ʙᴏᴛ', callback_data='clone')])
        
        await edit_menu_helper(
            query,
            text=script.START_TXT.format(query.from_user.mention, temp.U_NAME, temp.B_NAME),
            reply_markup=InlineKeyboardMarkup(buttons),
            photo="random"
        )
        await query.answer()
        
    elif data == "filters":
        buttons = [[
            InlineKeyboardButton('Mᴀɴᴜᴀʟ FIʟᴛᴇʀ', callback_data='manuelfilter'),
            InlineKeyboardButton('Aᴜᴛᴏ FIʟᴛᴇʀ', callback_data='autofilter')
        ],[
            InlineKeyboardButton('⟸ Bᴀᴄᴋ', callback_data='help'),
            InlineKeyboardButton('Gʟᴏʙᴀʟ Fɪʟᴛᴇʀs', callback_data='global_filters')
        ]]
        await edit_menu_helper(
            query,
            text=script.ALL_FILTERS.format(query.from_user.mention),
            reply_markup=InlineKeyboardMarkup(buttons),
            photo="random"
        )
        await query.answer()

    elif data == "global_filters":
        buttons = [[InlineKeyboardButton('⟸ Bᴀᴄᴋ', callback_data='filters')]]
        await edit_menu_helper(
            query,
            text=script.GFILTER_TXT,
            reply_markup=InlineKeyboardMarkup(buttons),
            photo="random"
        )
        await query.answer()
    
    elif data == "help":
        buttons = [[
             InlineKeyboardButton('⚙️ ᴀᴅᴍɪɴ ᴏɴʟʏ 🔧', callback_data='admin'),
         ], [ 
             InlineKeyboardButton('ꜰɪʟᴇ ꜱᴛᴏʀᴇ', callback_data='store_file'),   
             InlineKeyboardButton('ᴛᴇʟᴇɢʀᴀᴘʜ', callback_data='tele') 
         ], [ 
             InlineKeyboardButton('ᴄᴏɴɴᴇᴄᴛɪᴏɴꜱ', callback_data='coct'), 
             InlineKeyboardButton('ꜰɪʟᴛᴇʀꜱ', callback_data='filters')
         ], [
             InlineKeyboardButton('ꜱᴛɪᴄᴋᴇʀ-ɪᴅ', callback_data='sticker'),             
             InlineKeyboardButton('🏠 𝙷𝙾𝙼𝙴 🏠', callback_data='start')
        ]]
        await edit_menu_helper(
            query,
            text=script.HELP_TXT.format(query.from_user.mention),
            reply_markup=InlineKeyboardMarkup(buttons),
            photo="random"
        )
        await query.answer()

    elif data == "about":
        buttons = [[
            InlineKeyboardButton('Sᴜᴘᴘᴏʀᴛ Gʀᴏᴜᴘ', url=GRP_LNK),
            InlineKeyboardButton('Sᴏᴜʀᴄᴇ Cᴏᴅᴇ', url="https://t.me/Kannada_Filmy_Club")
        ],[
            InlineKeyboardButton('Hᴏᴍᴇ', callback_data='start'),
            InlineKeyboardButton('Cʟᴏsᴇ', callback_data='close_data')
        ]]
        await edit_menu_helper(
            query,
            text=script.ABOUT_TXT.format(temp.U_NAME, temp.B_NAME, OWNER_LNK),
            reply_markup=InlineKeyboardMarkup(buttons),
            photo="random"
        )
        await query.answer()

    elif data == "subscription":
        buttons = [[InlineKeyboardButton('⇚Back', callback_data='start')]]
        await edit_menu_helper(
            query,
            text=script.SUBSCRIPTION_TXT.format(REFERAL_PREMEIUM_TIME, temp.U_NAME, query.from_user.id, REFERAL_COUNT),
            reply_markup=InlineKeyboardMarkup(buttons),
            photo="random"
        )
        await query.answer()

    elif data == "manuelfilter":
        buttons = [[
            InlineKeyboardButton('⟸ Bᴀᴄᴋ', callback_data='filters'),
            InlineKeyboardButton('Bᴜᴛᴛᴏɴs', callback_data='button')
        ]]
        await edit_menu_helper(
            query,
            text=script.MANUELFILTER_TXT,
            reply_markup=InlineKeyboardMarkup(buttons),
            photo="random"
        )
        await query.answer()

    elif data == "button":
        buttons = [[InlineKeyboardButton('⟸ Bᴀᴄᴋ', callback_data='manuelfilter')]]
        await edit_menu_helper(
            query,
            text=script.BUTTON_TXT,
            reply_markup=InlineKeyboardMarkup(buttons),
            photo="random"
        )
        await query.answer()

    elif data == "autofilter":
        buttons = [[InlineKeyboardButton('⟸ Bᴀᴄᴋ', callback_data='filters')]]
        await edit_menu_helper(
            query,
            text=script.AUTOFILTER_TXT,
            reply_markup=InlineKeyboardMarkup(buttons),
            photo="random"
        )
        await query.answer()

    elif data == "coct":
        buttons = [[InlineKeyboardButton('⟸ Bᴀᴄᴋ', callback_data='help')]]
        await edit_menu_helper(
            query,
            text=script.CONNECTION_TXT,
            reply_markup=InlineKeyboardMarkup(buttons),
            photo="random"
        )
        await query.answer()

    elif data == "admin":
        buttons = [[
            InlineKeyboardButton('⟸ Bᴀᴄᴋ', callback_data='help'),
            InlineKeyboardButton('ᴇxᴛʀᴀ', callback_data='extra')
        ]]
        await edit_menu_helper(
            query,
            text=script.ADMIN_TXT,
            reply_markup=InlineKeyboardMarkup(buttons),
            photo="random"
        )
        await query.answer()
    
    elif data == "store_file":
        buttons = [[InlineKeyboardButton('⟸ Bᴀᴄᴋ', callback_data='help')]]
        await edit_menu_helper(
            query,
            text=script.FILE_STORE_TXT,
            reply_markup=InlineKeyboardMarkup(buttons),
            photo="random"
        )
        await query.answer()

    elif data == "r_txt":
        buttons = [[InlineKeyboardButton('⟸ Bᴀᴄᴋ', callback_data='help')]]
        await edit_menu_helper(
            query,
            text=script.RENAME_TXT,
            reply_markup=InlineKeyboardMarkup(buttons),
            photo="random"
        )
        await query.answer()

    elif data == "s_txt":
        buttons = [[InlineKeyboardButton('⟸ Bᴀᴄᴋ', callback_data='help')]]
        await edit_menu_helper(
            query,
            text=script.STREAM_TXT,
            reply_markup=InlineKeyboardMarkup(buttons),
            photo="random"
        )
        await query.answer()
    
    elif data == "extra":
        buttons = [[InlineKeyboardButton('⟸ Bᴀᴄᴋ', callback_data='admin')]]
        await edit_menu_helper(
            query,
            text=script.EXTRAMOD_TXT.format(OWNER_LNK, CHNL_LNK),
            reply_markup=InlineKeyboardMarkup(buttons),
            photo="random"
        )
        await query.answer()

    elif data == "stats":
        buttons = [[
            InlineKeyboardButton('⟸ Bᴀᴄᴋ', callback_data='help'),
            InlineKeyboardButton('⟲ Rᴇғʀᴇsʜ', callback_data='rfrsh')
        ]]
        stats_text = await get_stats_text()
        await edit_menu_helper(
            query,
            text=stats_text,
            reply_markup=InlineKeyboardMarkup(buttons),
            photo="random"
        )
        await query.answer()

    elif data == "rfrsh":
        await query.answer("Fetching MongoDb DataBase")
        buttons = [[
            InlineKeyboardButton('⟸ BᴀᴄK', callback_data='help'),
            InlineKeyboardButton('⟲ Rᴇғʀᴇsʜ', callback_data='rfrsh')
        ]]
        stats_text = await get_stats_text()
        await edit_menu_helper(
            query,
            text=stats_text,
            reply_markup=InlineKeyboardMarkup(buttons),
            photo="random"
        )

    elif data == "shortlink_info":
        btn = [[
            InlineKeyboardButton("👇Select Your Language 👇", callback_data="laninfo")
        ],[
            InlineKeyboardButton("English", callback_data="english_info"),
        ],[
            InlineKeyboardButton("⟸ Bᴀᴄᴋ", callback_data="start")
        ]]
        await edit_menu_helper(
            query,
            text=script.SHORTLINK_INFO,
            reply_markup=InlineKeyboardMarkup(btn),
            photo="random"
        )
        await query.answer()

    elif data == "tele":
        btn = [[
            InlineKeyboardButton("⟸ Bᴀᴄᴋ", callback_data="help"),
            InlineKeyboardButton("Cᴏɴᴛᴀᴄᴛ", url="telegram.me/Sandalwood_man")
        ]]
        await edit_menu_helper(
            query,
            text=script.TELE_TXT,
            reply_markup=InlineKeyboardMarkup(btn),
            photo="random"
        )
        await query.answer()

    elif data == "sticker":
        btn = [[
            InlineKeyboardButton("⟸ Bᴀᴄᴋ", callback_data="help"),
            InlineKeyboardButton("Cᴏɴᴛᴀᴄᴛ", url="telegram.me/Sandalwood_man")
        ]]
        await edit_menu_helper(
            query,
            text=script.STICKER_TXT,
            reply_markup=InlineKeyboardMarkup(btn),
            photo="random"
        )
        await query.answer()

    elif data == "english_info":
        btn = [[
            InlineKeyboardButton("⟸ Bᴀᴄᴋ", callback_data="start"),
            InlineKeyboardButton("Cᴏɴᴛᴀᴄᴛ", url="telegram.me/Sandalwood_man")
        ]]
        await edit_menu_helper(
            query,
            text=script.ENGLISH_INFO,
            reply_markup=InlineKeyboardMarkup(btn),
            photo="random"
        )
        await query.answer()


async def auto_filter(client, name, msg, reply_msg, ai_search, spoll=False):
    curr_time = datetime.now(pytz.timezone('Asia/Kolkata')).time()
    
    if not spoll:
        message = msg
        if message.text.startswith("/"): return
        if re.findall("((^\/|^,|^!|^\.|^[\U0001F600-\U000E007F]).*)", message.text):
            return
        
        search = name.lower()
        if len(search) < 100:
            find = search.split(" ")
            search = ""
            removes = ["in","upload", "series", "full", "horror", "thriller", "mystery", "print", "file"]
            search = " ".join([x for x in find if x not in removes])
            
            search = re.sub(r"\b(pl(i|e)*?(s|z+|ease|se|ese|(e+)s(e)?)|((send|snd|giv(e)?|gib)(\sme)?)|movie(s)?|new|latest|bro|bruh|broh|helo|that|find|dubbed|link|venum|iruka|pannunga|pannungga|anuppunga|anupunga|anuppungga|anupungga|film|undo|kitti|kitty|tharu|kittumo|kittum|movie|any(one)|with\ssubtitle(s)?)", "", search, flags=re.IGNORECASE)
            search = re.sub(r"[\-\.:]", " ", search)
            search = re.sub(r"\s+", " ", search).strip()
            
            settings = await get_settings(message.chat.id)
            
            # --- MODIFICATION: Set limit based on button/text mode ---
            limit = 100 if settings.get("button", True) else 60
            
            files, offset, total_results = await get_search_results(message.chat.id, search, offset=0, filter=True, limit=limit)
            
            if not files:
                if settings.get("spell_check", True):
                    return await advantage_spell_chok(client, name, msg, reply_msg, ai_search)
                else:
                    # Deleting "Searching..." message if no results
                    try:
                        await reply_msg.delete()
                    except:
                        pass
                    return
        else:
            return # Message too long
    else:
        # Coming from spell check callback
        message = msg.message.reply_to_message
        search, files, offset, total_results = spoll
        settings = await get_settings(message.chat.id)
        await msg.message.delete() # Delete the spell check suggestion message

    pre = 'filep' if settings.get('file_secure', False) else 'file'
    key = f"{message.chat.id}-{message.id}"
    req = message.from_user.id if message.from_user else 0
    FRESH[key] = search
    temp.GETALL[key] = files
    temp.SHORT[message.from_user.id] = message.chat.id

    if settings.get("button", True):
        btn = [
            [
                InlineKeyboardButton(
                    text=f"[{get_size(file['file_size'])}] {' '.join(filter(lambda x: not x.startswith('[') and not x.startswith('@') and not x.startswith('www.'), file['file_name'].split()))}", 
                    callback_data=f'{pre}#{file["file_id"]}'
                ),
            ]
            for file in files
        ]
        btn.insert(0, [InlineKeyboardButton("•  Bᴀᴄᴋ Uᴘ CʜᴀNNᴇʟ  •", url="https://t.me/KR_PICTURE")])
    else:
        btn = [[InlineKeyboardButton("•  Bᴀᴄᴋ Uᴘ CʜᴀNNᴇʟ  •", url="https://t.me/KR_PICTURE")]]

    # --- MODIFICATION: Removed all pagination logic ---
    btn.append(
        [
            InlineKeyboardButton(
                "🎥 ಕನ್ನಡ ಹೊಸ ಮೂವೀಗಳು 🎥", url="https://t.me/KR_PICTURE"
            )
        ]
    )
    # --- END MODIFICATION ---
        
    imdb = await get_poster(search, file=(files[0])['file_name']) if settings.get("imdb", True) else None
    
    cur_time = datetime.now(pytz.timezone('Asia/Kolkata')).time()
    time_difference = timedelta(hours=cur_time.hour, minutes=cur_time.minute, seconds=(cur_time.second+(cur_time.microsecond/1000000))) - timedelta(hours=curr_time.hour, minutes=curr_time.minute, seconds=(curr_time.second+(curr_time.microsecond/1000000)))
    remaining_seconds = "{:.2f}".format(time_difference.total_seconds())
    
    cap = ""
    if imdb:
        TEMPLATE = script.IMDB_TEMPLATE_TXT
        cap = TEMPLATE.format(
            qurey=search,
            title=imdb.get('title', "N/A"),
            votes=imdb.get('votes', "N/A"),
            aka=imdb.get("aka", "N/A"),
            seasons=imdb.get("seasons", "N/A"),
            box_office=imdb.get('box_office', "N/A"),
            localized_title=imdb.get('localized_title', "N/A"),
            kind=imdb.get('kind', "N/A"),
            imdb_id=imdb.get("imdb_id", "N/A"),
            cast=imdb.get("cast", "N/A"),
            runtime=imdb.get("runtime", "N/A"),
            countries=imdb.get("countries", "N/A"),
            certificates=imdb.get("certificates", "N/A"),
            languages=imdb.get("languages", "N/A"),
            director=imdb.get("director", "N/A"),
            writer=imdb.get("writer", "N/A"),
            producer=imdb.get("producer", "N/A"),
            composer=imdb.get("composer", "N/A"),
            cinematographer=imdb.get("cinematographer", "N/A"),
            music_team=imdb.get("music_team", "N/A"),
            distributors=imdb.get("distributors", "N/A"),
            release_date=imdb.get('release_date', "N/A"),
            year=imdb.get('year', "N/A"),
            genres=imdb.get('genres', "N/A"),
            poster=imdb.get('poster', "N/A"),
            plot=imdb.get('plot', "N/A"),
            rating=imdb.get('rating', "N/A"),
            url=imdb.get('url', "N/A"),
            **locals()
        )
        temp.IMDB_CAP[message.from_user.id] = cap
    else:
        cap = f"<b>Tʜᴇ Rᴇꜱᴜʟᴛꜱ Fᴏʀ ☞ {search}\n\nRᴇǫᴜᴇsᴛᴇᴅ Bʏ ☞ {message.from_user.mention}\n\nʀᴇsᴜʟᴛ sʜᴏᴡ ɪɴ ☞ {remaining_seconds} sᴇᴄᴏɴᴅs\n\nᴘᴏᴡᴇʀᴇᴅ ʙʏ ☞ : {message.chat.title} \n\n⚠️ ᴀꜰᴛᴇʀ 5 ᴍɪɴᴜᴛᴇꜱ ᴛʜɪꜱ ᴍᴇꜱꜱᴀɢᴇ ᴡɪʟʟ ʙᴇ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ ᴅᴇʟᴇᴛᴇᴅ 🗑️\n\n</b>"

    if not settings.get("button", True):
        cap += "<b>\n\n<u>🍿 Your Movie Files 👇</u></b>\n"
        for file in files:
            cap += f"<b>\n📁 <a href='https://telegram.me/{temp.U_NAME}?start=files_{file['file_id']}'>[{get_size(file['file_size'])}] {' '.join(filter(lambda x: not x.startswith('[') and not x.startswith('@') and not x.startswith('www.'), file['file_name'].split()))}\n</a></b>"

    sent_message = None
    if imdb and imdb.get('poster'):
        try:
            sent_message = await message.reply_photo(
                photo=imdb.get('poster'), 
                caption=cap, 
                reply_markup=InlineKeyboardMarkup(btn)
            )
            await reply_msg.delete()
        except (MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty):
            pic = imdb.get('poster').replace('.jpg', "._V1_UX360.jpg")
            try:
                sent_message = await message.reply_photo(
                    photo=pic, 
                    caption=cap, 
                    reply_markup=InlineKeyboardMarkup(btn)
                )
                await reply_msg.delete()
            except Exception as e:
                logger.exception(f"Error sending resized poster: {e}")
                sent_message = await reply_msg.edit_text(text=cap, reply_markup=InlineKeyboardMarkup(btn), disable_web_page_preview=True)
        except Exception as e:
            logger.exception(e) 
            sent_message = await reply_msg.edit_text(text=cap, reply_markup=InlineKeyboardMarkup(btn), disable_web_page_preview=True)
    else:
        sent_message = await reply_msg.edit_text(text=cap, reply_markup=InlineKeyboardMarkup(btn), disable_web_page_preview=True)
        
    if sent_message and settings.get('auto_delete', False):
        await asyncio.sleep(300) # 5 minutes
        try:
            await sent_message.delete()
            await message.delete()
        except Exception:
            pass # Message might have been deleted already

async def advantage_spell_chok(client, name, msg, reply_msg, vj_search):
    mv_id = msg.id
    mv_rqst = name
    reqstr1 = msg.from_user.id if msg.from_user else 0
    reqstr = await client.get_users(reqstr1)
    
    query = re.sub(
        r"\b(pl(i|e)*?(s|z+|ease|se|ese|(e+)s(e)?)|((send|snd|giv(e)?|gib)(\sme)?)|movie(s)?|new|latest|br((o|u)h?)*|^h(e|a)?(l)*(o)*|mal(ayalam)?|t(h)?amil|file|that|find|und(o)*|kit(t(i|y)?)?o(w)?|thar(u)?(o)*w?|kittum(o)*|aya(k)*(um(o)*)?|full\smovie|any(one)|with\ssubtitle(s)?)",
        "", msg.text, flags=re.IGNORECASE
    )
    query = query.strip() + " movie"
    
    try:
        movies = await get_poster(mv_rqst, bulk=True)
    except Exception as e:
        logger.exception(e)
        movies = None

    button = [[InlineKeyboardButton("🎥 ಕನ್ನಡ ಹೊಸ ಮೂವೀಗಳು 🎥", url="https://t.me/KR_PICTURE")]]
    
    if not movies:
        if NO_RESULTS_MSG:
            await client.send_message(chat_id=LOG_CHANNEL, text=(script.NORSLTS.format(reqstr.id, reqstr.mention, mv_rqst)))
        
        # Deleting "Searching..." message if no results
        try:
            await reply_msg.delete()
        except:
            pass
        return

    movielist = [movie.get('title') for movie in movies if movie.get('title')]
    movielist += [f"{movie.get('title')} {movie.get('year')}" for movie in movies if movie.get('title') and movie.get('year')]
    
    if not movielist:
        if NO_RESULTS_MSG:
            await client.send_message(chat_id=LOG_CHANNEL, text=(script.NORSLTS.format(reqstr.id, reqstr.mention, mv_rqst)))
        
        # Deleting "Searching..." message if no results
        try:
            await reply_msg.delete()
        except:
            pass
        return

    SPELL_CHECK[mv_id] = movielist
    
    if AI_SPELL_CHECK and vj_search:
        vj_search_new = False
        await reply_msg.edit_text("<b><i>I Am Trying To Find Your Movie With Your Wrong Spelling.</i></b>")
        
        movienamelist = [movie.get('title') for movie in movies if movie.get('title')]
        for techvj in movienamelist:
            if mv_rqst.capitalize().startswith(techvj[0]):
                await auto_filter(client, techvj, msg, reply_msg, vj_search_new)
                return # Found a match
        
        # If AI check fails, fall through to showing buttons
        pass # Fall through to suggestion buttons

    # Show suggestion buttons
    btn = [
        [InlineKeyboardButton(text=movie_name.strip(), callback_data=f"spol#{reqstr1}#{k}")]
        for k, movie_name in enumerate(movielist[:10]) # Limit to 10 suggestions
    ]
    btn.append([InlineKeyboardButton(text="Close", callback_data=f'spol#{reqstr1}#close_spellcheck')])
    
    spell_check_del = await reply_msg.edit_text(
        text=script.CUDNT_FND.format(mv_rqst),
        reply_markup=InlineKeyboardMarkup(btn)
    )
    
    settings = await get_settings(msg.chat.id)
    if settings.get('auto_delete', False):
        await asyncio.sleep(600)
        try:
            await spell_check_del.delete()
        except:
            pass

async def manual_filters(client, message, text=False):
    group_id = message.chat.id
    name = text or message.text
    reply_id = message.reply_to_message.id if message.reply_to_message else message.id
    keywords = await get_filters(group_id)
    
    for keyword in reversed(sorted(keywords, key=len)):
        pattern = r"( |^|[^\w])" + re.escape(keyword) + r"( |$|[^\w])"
        if re.search(pattern, name, flags=re.IGNORECASE):
            reply_text, btn, alert, fileid = await find_filter(group_id, keyword)

            if reply_text:
                reply_text = reply_text.replace("\\n", "\n").replace("\\t", "\t")

            settings = await get_settings(group_id)
            joelkb = None
            
            try:
                if fileid == "None":
                    if btn == "[]":
                        joelkb = await client.send_message(
                            group_id, 
                            reply_text, 
                            disable_web_page_preview=True,
                            protect_content=settings.get("file_secure", False),
                            reply_to_message_id=reply_id
                        )
                    else:
                        button = eval(btn)
                        joelkb = await client.send_message(
                            group_id,
                            reply_text,
                            disable_web_page_preview=True,
                            reply_markup=InlineKeyboardMarkup(button),
                            protect_content=settings.get("file_secure", False),
                            reply_to_message_id=reply_id
                        )
                elif btn == "[]":
                    joelkb = await client.send_cached_media(
                        group_id,
                        fileid,
                        caption=reply_text or "",
                        protect_content=settings.get("file_secure", False),
                        reply_to_message_id=reply_id
                    )
                else:
                    button = eval(btn)
                    joelkb = await message.reply_cached_media(
                        fileid,
                        caption=reply_text or "",
                        reply_markup=InlineKeyboardMarkup(button),
                        reply_to_message_id=reply_id
                    )
            except Exception as e:
                logger.exception(e)
                return True # Still counts as handled

            # Simplified auto-filter and auto-delete logic
            auto_ffilter = settings.get('auto_ffilter', True)
            auto_delete = settings.get('auto_delete', False)
            
            if auto_ffilter and not text: # Don't auto-filter on spell-check callbacks
                ai_search = True
                reply_msg = await message.reply_text(f"<b><i>Searching For {message.text} 🔍</i></b>")
                await auto_filter(client, message.text, message, reply_msg, ai_search)
                if auto_delete and joelkb:
                    try:
                        await joelkb.delete()
                    except Exception:
                        pass
            elif auto_delete and joelkb:
                await asyncio.sleep(600)
                try:
                    await joelkb.delete()
                except Exception:
                    pass
            
            return True # Filter was found and handled
            
    return False # No filter found

async def global_filters(client, message, text=False):
    group_id = message.chat.id
    name = text or message.text
    reply_id = message.reply_to_message.id if message.reply_to_message else message.id
    keywords = await get_gfilters('gfilters')
    
    for keyword in reversed(sorted(keywords, key=len)):
        pattern = r"( |^|[^\w])" + re.escape(keyword) + r"( |$|[^\w])"
        if re.search(pattern, name, flags=re.IGNORECASE):
            reply_text, btn, alert, fileid = await find_gfilter('gfilters', keyword)

            if reply_text:
                reply_text = reply_text.replace("\\n", "\n").replace("\\t", "\t")

            settings = await get_settings(group_id)
            joelkb = None
            
            try:
                if fileid == "None":
                    if btn == "[]":
                        joelkb = await client.send_message(
                            group_id, 
                            reply_text, 
                            disable_web_page_preview=True,
                            reply_to_message_id=reply_id
                        )
                    else:
                        button = eval(btn)
                        joelkb = await client.send_message(
                            group_id,
                            reply_text,
                            disable_web_page_preview=True,
                            reply_markup=InlineKeyboardMarkup(button),
                            reply_to_message_id=reply_id
                        )
                elif btn == "[]":
                    joelkb = await client.send_cached_media(
                        group_id,
                        fileid,
                        caption=reply_text or "",
                        reply_to_message_id=reply_id
                    )
                else:
                    button = eval(btn)
                    joelkb = await message.reply_cached_media(
                        fileid,
                        caption=reply_text or "",
                        reply_markup=InlineKeyboardMarkup(button),
                        reply_to_message_id=reply_id
                    )
            except Exception as e:
                logger.exception(e)
                return True

            # Chain to manual filters, as per original logic
            manual_handled = await manual_filters(client, message, text)
            
            # Simplified auto-filter and auto-delete logic
            auto_ffilter = settings.get('auto_ffilter', True)
            auto_delete = settings.get('auto_delete', False)
            
            if not manual_handled and auto_ffilter and not text:
                ai_search = True
                reply_msg = await message.reply_text(f"<b><i>Searching For {message.text} 🔍</i></b>")
                await auto_filter(client, message.text, message, reply_msg, ai_search)
                if auto_delete and joelkb:
                    try:
                        await joelkb.delete()
                    except Exception:
                        pass
            elif auto_delete and joelkb:
                if manual_handled: # If manual filter was also sent, delete global reply sooner
                     try:
                        await joelkb.delete()
                     except Exception:
                        pass
                else:
                    await asyncio.sleep(600)
                    try:
                        await joelkb.delete()
                    except Exception:
                        pass
            
            return True # Global filter was found and handled

    return False # No global filter found
