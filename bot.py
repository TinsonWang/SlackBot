from operator import contains
import os
import logging
from time import sleep
import dotenv
from flask import Flask, request, Response
from slack import WebClient
from slackeventsapi import SlackEventAdapter
from pathlib import Path
from re import search
import random
import requests
import json

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

## Why does this send twice?
# client.chat_postMessage(channel="#general", text="TinsonBot reporting for duty!")

# Store message counts for all users in a dictionary -- This should be moved into an SQL database
message_counts = {}
welcome_messages = {}

# Referenced from: https://github.com/wesbos/dad-jokes
bad_jokes_fp = open("badjokes.txt")
bad_jokes = bad_jokes_fp.readlines()

class WelcomeMessage:
    START_TEXT = {
        'type': 'section',
        'text': {
            'type': 'mrkdwn',
            'text': (
                'Welcome to my testing channel. \n\n'
                '*Please click this button!*'
            )
        }
    }

    DIVIDER = {'type': 'divider'}

    def __init__(self, channel, user):
        self.channel = channel
        self.user = user
        self.icon_emoji = ':robot_face:'
        self.timestamp = ''
        self.completed = False

    def get_message(self):
        return {
            'ts': self.timestamp,
            'channel': self.channel,
            'username': 'Welcome Robot!',
            'icon_emoji': self.icon_emoji,
            'blocks': [
                self.START_TEXT,
                self.DIVIDER,
                self._get_reaction_task()
            ]
        }

    def _get_reaction_task(self):
        checkmark = ':white_check_mark:'
        if not self.completed:
            checkmark = ':white_large_square:'

        text = f'{checkmark} *React to this message!*'

        return {
            'type': 'section',
            'text': {
                'type':'mrkdwn',
                'text': text
            }
        }

def send_welcome_message(channel, user):
    welcome = WelcomeMessage(channel, user)
    message = welcome.get_message()
    response = client.chat_postMessage(**message)
    welcome.timestamp = response['ts']

    if channel not in welcome_messages:
        welcome_messages[channel] = {}

    welcome_messages[channel][user] = welcome

# Handler for message sent event (When a message is sent, call this function)
@slack_event_adapter.on("message")
def message(payload):
    event = payload.get('event', {})
    channel_id = event.get('channel')
    user_id = event.get('user')
    text = event.get('text')
    text = text.lower()

    if user_id != None and BOT_ID != user_id:

        # If user already exists, increment their message count, else set it to 1
        if user_id in message_counts:
            message_counts[user_id] += 1
        else:
            message_counts[user_id] = 1

        # client.chat_postMessage(channel=channel_id, text=text + " (ECHO)")

        # Currently returns weather information for Ontario -- add more interactivity later by allowing user to specify location
        if search("!weather", text):
            lat = "34.063343"
            lon = "-117.650887"
            weather_url = "https://api.openweathermap.org/data/2.5/weather?lat=%s&lon=%s&appid=%s&units=metric" % (lat, lon, os.environ['WEATHER_TOKEN'])
            weather_response = requests.get(weather_url)
            data = json.loads(weather_response.text)
            weather_data = data['main']
            weather_current = data['weather'][0]['main']
            weather_current_desc = data['weather'][0]['description']
            weather_temperature = weather_data['temp']
            weather_feels_like = weather_data['feels_like']
            weather_humidity = weather_data['humidity']
            new_line = '\n'
            weather_message = f'Currently: {weather_current} -- {weather_current_desc} {new_line} Temperature: {weather_temperature}°C {new_line} Feels Like: {weather_feels_like}°C {new_line} Humidity: {weather_humidity}% {new_line} {new_line} Data provided by OpenWeather API'
            client.chat_postMessage(channel=channel_id, text=f'{weather_message}', icon_emoji=":sunny:", username="Weather Report")

            # client.chat_postMessage(channel=channel_id, text="Placeholder message for weather information")

        if search("!joke", text):

            ## ASYNC ISSUES?
            # random_int = random.randint(0, 286)
            # found_joke = False

            # while found_joke != False:
            #     if search("**Q:**", bad_jokes[random_int]) != None and random_int % 2 == 0:
            #         found_joke = True
            #     else:
            #         random_int = random.randint(0, 286)

            # joke = bad_jokes[random_int]
            # answer = bad_jokes[random_int+1]
            # new_line = '\n\n'

            # client.chat_postMessage(channel=channel_id, text=f'{joke}')
            # sleep(1)
            # client.chat_postMessage(channel=channel_id, text=f'{answer}')

            client.chat_postMessage(channel=channel_id, text="Insert some joke here from some pool?")


        if search("!messagecount", text):
            client.chat_postMessage(channel=channel_id, text="Temporary Message")

        if search("!help", text):
            client.chat_postMessage(channel=channel_id, text="Did you ask me a question?")

        if text == "!tasktest":
            send_welcome_message(channel_id, user_id)

            ## Direct DM
            # send_welcome_message(f'@{user_id}', user_id)


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




