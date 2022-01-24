from google_trans_new import LANGUAGES

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
