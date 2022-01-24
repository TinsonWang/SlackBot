from google_trans_new import LANGUAGES

async def languages_top(message):

    languages = "'cht' : 'chinese (traditional)'\n" \
                "'chs' : 'chinese (simplified)'\n" \
                "'fil' : 'filipino'\n" \
                "'fr' : 'french'\n" \
                "'de' : 'german'\n" \
                "'ja' : 'japanese'\n" \
                "'ko' : 'korean'\n" \
                "'pt' : 'portugese'\n" \
                "'es' : 'spanish'\n" \
                "'vi' : 'vietnamese'"

    await message.channel.send("Here's a list of the most frequently used languages:\n\n"
                               +languages
                               +'\n\nFor a full list of languages available, use !lang_all')
    return

def translate_message(bot, channel, text):
    # Extracts the 'destination code' from the command
    src = text[1:3]

    if (text[7].isspace()):
        dest = text[5:7]
        message = text[8:]
    else:
        dest = text[5:8]
        message = text[9:]

    if dest == 'chs':
        dest = 'zh-cn'

    if dest == 'cht':
        dest = 'zh-tw'

    if dest == 'jp':
        dest = 'ja'

    if dest not in LANGUAGES:
        bot.chat_postMessage(channel=channel, text="Invalid language code - try again?")
    else:
        message_translated = bot.translator.translate(message, lang_tgt=dest)
        translated_message = '[' + src + ' -> ' + dest + ']:\n' + message_translated
        bot.chat_postMessage(channel=channel, text=translated_message)
