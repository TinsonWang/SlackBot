import os
import logging
import dotenv
from flask import Flask, request, Response
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

# Store message counts for all users in a dictionary
message_counts = {}

# Handler for message sent event (When a message is sent, call this function)
@slack_event_adapter.on("message")
def message(payload):
    event = payload.get('event', {})
    channel_id = event.get('channel')
    user_id = event.get('user')
    text = event.get('text')

    if BOT_ID != user_id:

        # If user already exists, increment their message count, else set it to 1
        if user_id in message_counts:
            message_counts[user_id] += 1
        else:
            message_counts[user_id] = 1

        # client.chat_postMessage(channel=channel_id, text=text + " (ECHO)")

# Handler for error event
@slack_event_adapter.on("error")
def error_handler(err):
     print("ERROR: " + str(err))

# Route for /message-count
@app.route('/message-count', methods=['POST'])
def message_count():
    data = request.form
    user_id = data.get('user_id')
    user_name = data.get('user_name')
    channel_id = data.get('channel_id')

    # Get the message count from the dictionary using the user_id, if not found, set as 0
    message_count = message_counts.get(user_id, 0)

    client.chat_postMessage(channel=channel_id, text=f"Hi {user_name}, your message count is: {message_count}")
    return Response(), 200

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




