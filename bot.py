import logging
import re
import requests
import json
from bs4 import BeautifulSoup
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Filters,
    Updater,
    CommandHandler,
    CallbackQueryHandler,
    CallbackContext,
    MessageHandler,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)


def pythonanywhere_requests(url, clean=True):
    url = f"https://api.allorigins.win/get?callback=myFunc&url={url}"
    regex_command = r".{1,}\"contents\"\:\"(.{0,})\",\"status\""
    res = requests.get(url).text
    out = re.findall(regex_command, res)

    # enable this option when you want a html code(not json response)
    if clean == True:
        out = (
            out[0]
            .replace(r"\r", "")
            .replace(r"\n", "")
            .replace('\\"', '"')
            .replace(r"\t", "")
            .replace(": true", ": True")
            .replace(":true", ":True")
        )

    try:
        return out
    except Exception as e:
        raise e


def start(update: Update, context: CallbackContext):
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Hello! Welcome to Lyrics finder bot.\n"
        "You can use this bot to fetch lyrics from any song.\n"
        "Just type the name of the song you want the lyrics of, "
        "or part of it's lyrics.",
    )


def search(update: Update, context: CallbackContext):
    r = pythonanywhere_requests(
        f'https://genius.com/api/search/songs?q={update.message.text}', clean=False
    )

    global searchresults
    searchresults = [
        result["result"]
        # multiple `json.loads()` removes "\\"s and other unwanted characters from the raw response text
        for result in json.loads(json.loads(f'"{r[0]}"'))["response"]["sections"][0][
            "hits"
        ]
    ]

    # if no matches were found:
    if len(searchresults)==0:
        update.message.reply_text('No matches were found.\nPlease try another search.')
        return

    global urls
    urls = [result["url"] for result in searchresults]

    keyboard = [
        [
            InlineKeyboardButton(
                searchresults[num]['title']
                + ' by '
                + searchresults[num]['primary_artist']['name'],
                callback_data=num,
            )
        ]
        for num in range(len(searchresults))
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Choose a song:', reply_markup=reply_markup)


def button(update: Update, context: CallbackContext) -> None:
    """Sends lyrics when user chooses a song from the inline keyboard."""
    query = update.callback_query

    query.answer()

    r = pythonanywhere_requests(urls[int(query.data)])
    soup = BeautifulSoup(r.replace("<br/>", "\n").encode(), "html.parser")

    div = soup.find("div", class_=re.compile("^lyrics$|Lyrics__Root"))
    divtext = div.get_text()

    # remove '<TITLE by ARTIST>' and '<NUMBER>Embed' from lyrics
    for i in [0, -1, -2]:
        divtext = divtext.replace(div.__dict__["contents"][i].get_text(), "")

    # Fix missed empty lines between lyrics parts
    lyrics = divtext.replace("\n[", "\n\n[").replace("\n\n\n[", "\n\n[")

    # Split lyrics if length is more than 4096 characters
    if len(lyrics) > 4096:
        query.edit_message_text(text=lyrics[:4096])
        for p in range(int(len(lyrics) / 4096)):
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=lyrics[(p + 1) * 4096 : (p + 2) * 4096],
            )
    else:
        query.edit_message_text(text=lyrics)

    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Lyrics sent for "
        + searchresults[int(query.data)]["title"]
        + " by "
        + searchresults[int(query.data)]["primary_artist"]["name"]
        + ".",
    )


def main():
    TOKEN = "INSERT-YOUR-BOT-TOKEN-HERE"

    updater = Updater(TOKEN)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.text & (~Filters.command), search))
    dispatcher.add_handler(CallbackQueryHandler(button))

    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
