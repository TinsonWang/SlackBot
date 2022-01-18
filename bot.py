import os
import logging
import dotenv
from flask import Flask
from slack import WebClient
from slackeventsapi import SlackEventAdapter
from pathlib import Path

# Set up environment
env_path = Path('.') / '.env'
dotenv.load_dotenv(dotenv_path=env_path)

# Set up LOCAL Flask server
app = Flask(__name__)

# Set up event handler to send requests to Flask server endpoint using the signing secret
slack_event_adapter = SlackEventAdapter(os.environ['SIGNING_SECRET'], "/slack/events", app)

# Initialize Slack client
client = WebClient(token=os.environ['SLACK_TOKEN'])
BOT_ID = client.api_call("auth.test")['user_id']

client.chat_postMessage(channel="#general", text="Hello World!")

# Handler for message sent event (When a message is sent, call this function)
@slack_event_adapter.on("message")
def message(payload):
    event = payload.get('event', {})
    channel_id = event.get('channel')
    user_id = event.get('user')
    text = event.get('text')

    if BOT_ID != user_id:
        client.chat_postMessage(channel=channel_id, text=text + " (ECHO)")

# Error events
@slack_event_adapter.on("error")
def error_handler(err):
     print("ERROR: " + str(err))

if __name__ == "__main__":
    app.run(debug=True)









# Use ngrok to forward a public IP to our locally hosted server
# Run ngrok
# 'ngrok http 5000'
# client.chat_postMessage(channel="#slack-bot", text="Hello World!")
# client.chat_postMessage(channel="#general", text="Hello World!")
# user_list=client.users_list()
# for user in user_list['members']:
#     print(user['name'])




