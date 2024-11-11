import logging
import aiohttp
import re
import os
import random
import configparser
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup 
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, Application


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


config = configparser.ConfigParser()
config.read('config.ini')

URL = config['settings']['url']
X_API_KEY = config['settings']['x-api-key']
TOKEN = config['settings']['token']


async def caps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text_caps = ' '.join(context.args).upper()
    await context.bot.send_message(chat_id=update.effective_chat.id, text=text_caps)


async def info_template(update: Update, search_url, media_info_url, search_json, headers):
    async with aiohttp.ClientSession() as session:
        async with session.post(url=search_url, json=search_json, headers=headers) as resp:
            if resp.status == 200:
                detail_items = await resp.json()
                logger.info(detail_items)
                detail_items_data = detail_items.get("data").get("data")
                for detail in detail_items_data:
                    id = detail.get("id")
                    download_url = ""
                    gen_url = URL + "/api/torrent/genDlToken"
                    async with session.post(url=gen_url, params={"id": f"{id}"}, headers=headers) as gen_resp:
                        if gen_resp.status == 200:
                            download_data = await gen_resp.json()
                            download_url = download_data.get("data")
                    name = detail.get("name")
                    small_descr = detail.get("smallDescr")
                    image_list = detail.get("imageList")
                    image = image_list[0]
                    size_ori = detail.get("size")
                    size = format(int(size_ori) / 1024 / 1024 / 1024, '.2f') + " GB"
                    seeders = "seeders: " + detail.get("status").get("seeders")
                    leechers = "leechers: " + detail.get("status").get("leechers")
                    async with session.post(url=media_info_url, params={"id": id}, headers=headers) as resp:
                        if resp.status == 200:
                            media_info = await resp.json()
                            if "Chinese" in media_info.get("data"):
                                chinese = "中字"
                            else:
                                chinese = ""
                    caption = f"{name} {small_descr} {chinese} {size} {seeders} {leechers}"
                    keyboard = [
                        [
                            InlineKeyboardButton(
                                "Download", callback_data=download_url),
                            InlineKeyboardButton(
                                "Option 2", callback_data="1"),
                        ]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    try:
                        await update.message.reply_photo(photo=image, caption=caption, reply_markup=reply_markup)
                    except Exception as e:
                        await update.message.reply_photo(photo="https://www.pttime.org/pic/err_img.png", caption=caption, reply_markup=reply_markup)
    

async def get_free(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """mode will be normal,adult,movie,music,tvshow,waterfall,rss,rankings"""
    headers = {
        "x-api-key":X_API_KEY
    }
    search_url = URL + "/api/torrent/search"
    media_info_url = URL + "/api/torrent/mediaInfo"
    mode = update.message.text.split()[0].lstrip('/')
    logger.info(mode)
    try:
        keyword = update.message.text.split()[1]
    except IndexError as e:
        keyword = "free"
    try:
        pages = update.message.text.split()[2]
    except IndexError as e:
        pages = "3"
    if mode in ["normal", "adult", "movie", "tvshow", "waterfall", "rss", "rankings"]:
        if keyword == "free":
            search_json = {
                "mode":f"{mode}",
                "pageSize": int(pages),
                "discount":"FREE",
                "sortField":"LEECHERS",
            }
            await info_template(update, search_url=search_url, media_info_url=media_info_url, search_json=search_json, headers=headers)
        elif mode == "rankings" and keyword == "all":
            search_json = {
                "mode":f"{mode}",
                "pageSize": int(pages),
                "sortField": "SEEDERS",
            }
            await info_template(update, search_url=search_url, media_info_url=media_info_url, search_json=search_json, headers=headers)
        elif mode == "rankings" and keyword == "adult":
            search_json = {
                "mode":f"{mode}",
                "pageSize": int(pages),
                "categories": ["410", "429", "424","430","426","437","431","432","436","425","433","411","412","413","440"],
                "sortField": "SEEDERS",
            }
            await info_template(update, search_url=search_url, media_info_url=media_info_url, search_json=search_json, headers=headers)
        elif mode == "rankings" and keyword == "movie":
            search_json = {
                "mode":f"{mode}",
                "pageSize": int(pages),
                "categories": ["401", "419", "420","421","439"],
                "sortField": "SEEDERS",
            }
            await info_template(update, search_url=search_url, media_info_url=media_info_url, search_json=search_json, headers=headers)
        elif mode == "rankings" and keyword == "tvshow":
            search_json = {
                "mode":f"{mode}",
                "pageSize": int(pages),
                "categories": ["403", "402", "435","438"],
                "sortField": "SEEDERS",
            }
            await info_template(update, search_url=search_url, media_info_url=media_info_url, search_json=search_json, headers=headers)
        elif mode == "rankings" and keyword == "iv":
            search_json = {
                "mode":f"{mode}",
                "pageSize": int(pages),
                "categories": ["433", "425"],
                "sortField": "SEEDERS",
            }
            await info_template(update, search_url=search_url, media_info_url=media_info_url, search_json=search_json, headers=headers)
        else:       
            search_json = {
                "mode":f"{mode}",
                "keyword": f"{keyword}",
                "pageSize": int(pages),
                "sortField": "SEEDERS",
            }
            await info_template(update, search_url=search_url, media_info_url=media_info_url, search_json=search_json, headers=headers)

    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text=f"{mode}: Unknown Command.")
    


async def download_torrent(update: Update, context: ContextTypes.DEFAULT_TYPE, download_url, headers):
    download_dir = os.path.dirname(__file__)
    async with aiohttp.ClientSession() as session:
        async with session.get(download_url, headers=headers) as resp:
            if resp.status == 200:
                cd = resp.headers.get("content-disposition")
                try:
                    file_name = re.split(r'[;=]', cd)[2].strip('" ').encode("ISO-8859-1").decode()
                except Exception as e:
                    file_name = str(random.randint(100000, 999999)) + ".torrent"
                if not os.path.exists(f"{download_dir}/{file_name}"):
                    with open(f"{download_dir}/{file_name}", "wb") as f:
                        async for chunk in resp.content.iter_chunked(1024):
                            f.write(chunk)
                    await context.bot.send_message(chat_id=update.effective_chat.id, text="Done!")
                else:
                    await context.bot.send_message(chat_id=update.effective_chat.id, text="File exists!")



async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Parses the CallbackQuery and updates the message text."""
    headers = {
        "x-api-key":X_API_KEY
    }
    query = update.callback_query
    await query.answer()
    keyboard = [
        [
            InlineKeyboardButton("Downloading...", callback_data="1"),
            InlineKeyboardButton("Option 2", callback_data="2"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_reply_markup(reply_markup=reply_markup)
    await download_torrent(update=update, context=context, download_url=query.data, headers=headers)



async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display a help message"""
    await update.message.reply_text("""
1. /rankings all 3
2. /rankings movie 3
3. /rankings tvshow 3
4. /rankings adult 3
5. /rankings iv 3
6. /movie free 3 or /movie <name> 3
7. /adult free 3 or /adult <name> 3
8. /tvshow free 3 or /tvshow <name> 3
""")



async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Exception while handling an update:", exc_info=context.error)
    message = "error"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message)



if __name__ == '__main__':
    application = (
        Application.builder()
        .token(TOKEN)
        .arbitrary_callback_data(True)
        .build()
    )

    application.add_handler(CommandHandler('movie', get_free))
    application.add_handler(CommandHandler('adult', get_free))
    application.add_handler(CommandHandler('tvshow', get_free))
    application.add_handler(CommandHandler('rankings', get_free))
    application.add_handler(CommandHandler('help', help_handler))
    application.add_handler(CallbackQueryHandler(button))
    application.add_error_handler(error_handler)

    application.run_polling()
