import slack
import os
from pathlib import Path
import dotenv

env_path = Path('.') / '.env'
dotenv.load_dotenv(dotenv_path=env_path)

client = slack.WebClient(token=os.environ['SLACK_TOKEN'])
# client.chat_postMessage(channel="#slack-bot", text="Hello World!")
client.chat_postMessage(channel="#general", text="Hello World!")
