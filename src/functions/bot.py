from fnmatch import translate
from time import sleep
from operator import contains
import random
import logging

import os
import dotenv
import requests
import json
import slack
from flask import Flask, request, Response
from slackeventsapi import SlackEventAdapter
from pathlib import Path
from re import search, match
from google_trans_new import google_translator

from .task import *
from .translate import *


class TinsonBot(slack.WebClient):
    def __init__ (self, prefix, *args, **kwargs, ):
        super().__init__(*args, **kwargs)
        self.prefix = prefix

        # Store message counts for all users in a dictionary -- This should be moved into an SQL database
        self.message_counts = {}
        self.welcome_messages = {}
        self.translator = google_translator()

        # Set up environment
        env_path = Path('./src') / '.env'
        dotenv.load_dotenv(dotenv_path=env_path)

        # Referenced from: https://github.com/wesbos/dad-jokes
        self.bad_jokes_fp = open( Path('./src') / "badjokes.txt")
        self.bad_jokes = self.bad_jokes_fp.readlines()

        # Load in keys
        self.token = os.environ['SLACK_TOKEN']
        self.signing = os.environ['SIGNING_SECRET']
        self.weather_key = os.environ['WEATHER_TOKEN']

        # Initialize Slack client
        self.client = slack.WebClient(token=self.token)
        self.BOT_ID = self.client.api_call("auth.test")['user_id']

        # Start LOCAL Flask server
        self.server = Flask(__name__)

        # Set up event handler to send requests to Flask server endpoint using the signing secret
        self.slack_event_adapter = SlackEventAdapter(self.signing, "/slack/events", self.server)

        # Handler for message sent event (When a message is sent, call this function)
        @self.slack_event_adapter.on("message")
        def message(payload):
            # Fetch event details
            event = payload.get('event', {})
            channel_id = event.get('channel')
            user_id = event.get('user')
            text = event.get('text')

            try:
                text = text.lower()
            except AttributeError:
                pass


            if user_id != None and self.BOT_ID != user_id:
                # self.client.chat_postMessage(channel="#general", text="EVENT: Message detected!")

                # If user already exists, increment their message count, else set it to 1
                if user_id in self.message_counts:
                    self.message_counts[user_id] += 1
                else:
                    self.message_counts[user_id] = 1

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
                    self.client.chat_postMessage(channel=channel_id, text=f'{weather_message}', icon_emoji=":sunny:", username="Weather Report")

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
                    # client.chat_postMessage(channel=channel_id, text=f'{answer}')

                    self.client.chat_postMessage(channel=channel_id, text="Insert some joke here from some pool?")

                if search("!messagecount", text):
                    self.client.chat_postMessage(channel=channel_id, text="Temporary Message")

                if search("!help", text):
                    self.client.chat_postMessage(channel=channel_id, text="Did you ask me a question?")

                # Direct DM
                # send_welcome_message(f'@{user_id}', user_id)
                if text == "!tasktest":
                    self.send_welcome_message(channel_id, user_id)

                if match("![a-zA-Z][a-zA-Z]to[a-zA-Z][a-zA-Z]", text):
                    # self.client.chat_postMessage(channel=channel_id, text="Regex pattern found!")
                    translate_message(self, channel_id, text)


        # Handler for reaction added event
        @self.slack_event_adapter.on("reaction_added")
        def reaction(payload):
            # Fetch event details
            event = payload.get('event', {})
            channel_id = event.get('item', {}).get('channel')
            user_id = event.get('user')

            if user_id != None and self.BOT_ID != user_id:
                self.client.chat_postMessage(channel="#general", text="EVENT: Reaction detected!")

            if channel_id not in self.welcome_messages:
                return

            welcome = self.welcome_messages[channel_id][user_id]
            welcome.completed = True
            message = welcome.get_message()
            updated_message = self.client.chat_update(**message)
            welcome.timestamp = updated_message['ts']

        # Handler for error event
        @self.slack_event_adapter.on("error")
        def error_handler(err):
             print("ERROR: " + str(err))

        # Route for /message-count
        @self.server.route('/message-count', methods=['POST'])
        def message_count():
            data = request.form
            user_id = data.get('user_id')
            user_name = data.get('user_name')
            channel_id = data.get('channel_id')

            # Get the message count from the dictionary using the user_id, if not found, set as 0
            message_count = self.message_counts.get(user_id, 0)

            self.client.chat_postMessage(channel=channel_id, text=f"Hi {user_name}, your message count is: {message_count}")
            return Response(), 200

        # Start bot
        self.client.chat_postMessage(channel="#general", text="TinsonBot reporting for duty!")
        self.server.run()


    def send_welcome_message(self, channel, user):
        welcome = WelcomeMessage(channel, user)
        message = welcome.get_message()
        response = self.client.chat_postMessage(**message)
        welcome.timestamp = response['ts']

        if channel not in self.welcome_messages:
            self.welcome_messages[channel] = {}

        self.welcome_messages[channel][user] = welcome
