from time import sleep
import random
import logging
import asyncio

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
import mysql.connector

from .task import *
from .translate import *

from irc import server


class SlackBot(slack.WebClient):
    def __init__ (self, prefix, *args, **kwargs, ):
        super().__init__(*args, **kwargs)
        self.prefix = prefix

        # Store message counts for all users in a dictionary -- This should be moved into an SQL database
        self.message_counts = {}
        self.welcome_messages = {}
        self.translator = google_translator()

        # # Set up environment
        # env_path = Path('./src') / '.env'
        # dotenv.load_dotenv(dotenv_path=env_path)
        dotenv.load_dotenv(dotenv_path=r"***.env")

        # Referenced from: https://github.com/wesbos/dad-jokes
        # self.bad_jokes_fp = open(Path('./src') / "badjokes.txt", "r")
        self.bad_jokes_fp = open(r"***\badjokes.txt", "r")
        self.bad_jokes = self.bad_jokes_fp.readlines()

        # Load in keys
        self.token = os.environ['SLACK_TOKEN']
        self.signing = os.environ['SIGNING_SECRET']
        self.weather_key = os.environ['WEATHER_TOKEN']
        self.slack = os.environ['SQL_TOKEN']

        # Initialize Slack client
        self.client = slack.WebClient(token=self.token)
        self.BOT_ID = self.client.api_call("auth.test")['user_id']

        # Start LOCAL Flask server
        self.server = Flask(__name__)

        # Set up event handler to send requests to Flask server endpoint using the signing secret
        self.slack_event_adapter = SlackEventAdapter(self.signing, "/slack/events", self.server)

        # Establish connection to SQL Server
        db = mysql.connector.connect(
            host="localhost",
            user="root",
            password=f"{self.slack}",
            database="testdatabase"
        )

        self.cursor = db.cursor()

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

                if search("!readsql", text):
                    self.cursor.execute("SELECT * FROM Courses")
                    for x in self.cursor:
                        self.client.chat_postMessage(channel=channel_id, text=f"{x}")
                        self.client.chat_postMessage(channel=channel_id, text="--------------------")

                if search("!select", text):
                    selection = text[8:]
                    selection = selection.upper()
                    # self.client.chat_postMessage(channel=channel_id, text=f"USER REQUESTING QUERY FOR: {selection}")
                    successful_input = False
                    print(selection)
                    self.cursor.execute(f"SELECT * FROM Courses WHERE courseID = '{selection}'")
                    for x in self.cursor:
                        self.client.chat_postMessage(channel=channel_id, text=f"{x}")
                        successful_input = True

                    if not successful_input:
                        if search("CMySQLCursor", str(self.cursor)):
                            self.client.chat_postMessage(channel=channel_id, text=f"Could not query input: '{selection}'")

                if search("!insert", text):
                    selection = text[8:]
                    selection = selection.upper()

                    try:
                        self.cursor.execute(f"INSERT INTO Courses (courseID) VALUES (%s)", [f"{selection}"])
                        db.commit()
                        self.client.chat_postMessage(channel=channel_id, text=f"Added to table: '{selection}'")
                    except:
                        db.rollback()

                if search("!delete", text):
                    selection = text[8:]
                    selection = selection.upper()

                    try:
                        self.cursor.execute(f"DELETE FROM Courses WHERE courseID = '{selection}'")
                        db.commit()
                        self.client.chat_postMessage(channel=channel_id, text=f"Deleted from table: '{selection}'")
                    except:
                        db.rollback()

                if search("!execute", text):
                    text = event.get('text')
                    command = text[9:]

                    try:
                        self.cursor.execute(command)
                        db.commit()
                        self.client.chat_postMessage(channel=channel_id, text=f"Executed command: '{command}'")
                    except:
                        db.rollback()


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

        # Route for /help
        @self.server.route('/help', methods=['POST'])
        async def return_help():
            data = request.form
            user_id = data.get('user_id')
            user_name = data.get('user_name')
            channel_id = data.get('channel_id')

            help_response = {
                'channel': channel_id,
                'username': "Available Commands",
                'icon_emoji': ":question:",
                'blocks': [
                    {
                        'type': "section",
                        'text': {
                            'type': 'mrkdwn',
                            'text': (
                                "FORMAT\n"
                                "/command [parameters]                              || Description \n----------------------------------------------------------------------\n\n"
                                "/help                                                              || Describes all available commands\n"
                                "/weather [city] [state]                                  || Gets the weather at the specified location.\n"
                                "/joke                                                              || Returns a joke and answer pair.\n"
                                "/translate [2-letters] [2-letters] [message] || Translates from former to latter language.\n"
                                "/faq [forget][factoid string][?]                     || Removes/Adds/Returns factoid"
                            )
                        }
                    },
                    {
                        'type': "divider"
                    },
                    {
                        'type': "section",
                        'text': {
                            'type': 'mrkdwn',
                            'text': (
                                "*For further help:* \n"
                                "Slack: *** ****\n"
                                "Discord: ***#****\n"
                                "Email: ***@****\n"
                            )
                        }
                    }
                ]
            }

            self.client.chat_postMessage(**help_response)
            await(asyncio.sleep(1))
            return Response(), 200

        # Route for /weather
        @self.server.route('/weather', methods=['POST'])
        async def return_weather():
            data = request.form
            user_id = data.get('user_id')
            user_name = data.get('user_name')
            channel_id = data.get('channel_id')
            text = data.get('text')
            list = text.split(" ")
            city = list[0]
            state = list[1]

            try:
                location_url = "http://api.openweathermap.org/geo/1.0/direct?q=%s,%s&limit=1&appid=%s" % (city, state, os.environ['WEATHER_TOKEN'])
                location_response = requests.get(location_url)
                location_data = json.loads(location_response.text)
                lat = location_data[0]['lat']
                lon = location_data[0]['lon']
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
                weather_message = f'Weather Report for: {city}, {state}{new_line}Currently: {weather_current} -- {weather_current_desc} {new_line} Temperature: {weather_temperature}°C {new_line} Feels Like: {weather_feels_like}°C {new_line} Humidity: {weather_humidity}% {new_line} {new_line} Data provided by OpenWeather API'
                self.client.chat_postMessage(channel=channel_id, text=f'{weather_message}', icon_emoji=":sunny:", username="Weather Report")
                await asyncio.sleep(1)
                return Response(), 200
            except:
                self.client.chat_postMessage(channel=channel_id, text=f'Could not find weather data for: "{city}", "{state}"', icon_emoji=":sunny:", username="Weather Report")
                await asyncio.sleep(1)
                return Response(), 404

        # Route for /bucket-start
        @self.server.route('/bucket-start', methods=['POST'])
        def bucket_start():
            data = request.form
            user_id = data.get('user_id')
            user_name = data.get('user_name')
            channel_id = data.get('channel_id')

            server.main()

            return Response(), 200

        # Route for /bucket-send
        @self.server.route('/bucket-send', methods=['POST'])
        def bucket_test():
            data = request.form
            user_id = data.get('user_id')
            user_name = data.get('user_name')
            channel_id = data.get('channel_id')
            text = data.get('text')

            import sys
            import itertools
            import irc.client

            target = 'SLACK_BOT'
            "The nick or channel to which to send messages"

            # target='SLACK_BOT'
            # args = get_args()
            # jaraco.logging.setup(args)
            # target = args.target
            target = '***'
            server='127.0.0.1'
            port=6667
            nickname='SLACK_BOT'

            reactor = irc.client.Reactor()
            try:
                c = reactor.server().connect(server, port, nickname)
                c.privmsg(target, "This is a test")
                c.privmsg('bucketClone', "This is a test")
                c.privmsg('bucket', "This is a test")


                # self.client.chat_postMessage(channel=channel_id, text=f'{json.dumps(c.get_nickname())}')
                # self.client.chat_postMessage(channel=channel_id, text=f'{json.dumps(c.get_server_name())}')
                # self.client.chat_postMessage(channel=channel_id, text=f'{json.dumps(c.lusers(server))}')

                # c.disconnect("Command finished. Returning...")


                # c.send_items()


            except irc.client.ServerConnectionError:
                print(sys.exc_info()[1])
                raise SystemExit(1)

            # c.add_global_handler("welcome", on_connect)
            # c.add_global_handler("join", on_join)
            # c.add_global_handler("disconnect", on_disconnect)

            reactor.process_forever()

            return Response(), 200

        # Route for /joke
        @self.server.route('/joke', methods=['POST'])
        async def return_joke():
            data = request.form
            user_id = data.get('user_id')
            user_name = data.get('user_name')
            channel_id = data.get('channel_id')

            random_int = 1
            while random_int % 2 == 1:
                random_int = random.randint(0, 286)

            joke = self.bad_jokes[random_int]
            answer = self.bad_jokes[random_int+1]

            self.client.chat_postMessage(channel=channel_id, text=f'{joke}', icon_emoji = ":thinking_face:", username="Question")
            await asyncio.sleep(1)

            self.client.chat_postMessage(channel=channel_id, text=f'{answer}', icon_emoji = ":joy:", username="Answer")
            await asyncio.sleep(1)

            return Response(), 200

        # Route for /translate
        @self.server.route('/translate', methods=['POST'])
        async def translate():
            data = request.form
            user_id = data.get('user_id')
            user_name = data.get('user_name')
            channel_id = data.get('channel_id')
            text = data.get('text')
            translate_message_slash(self, channel_id, text)
            await asyncio.sleep(1)
            return Response(), 200

        # Route for /message-count
        @self.server.route('/message-count', methods=['POST'])
        async def message_count():
            data = request.form
            user_id = data.get('user_id')
            user_name = data.get('user_name')
            channel_id = data.get('channel_id')

            # Get the message count from the dictionary using the user_id, if not found, set as 0
            message_count = self.message_counts.get(user_id, 0)

            self.client.chat_postMessage(channel=channel_id, text=f"Hi {user_name}, your message count is: {message_count}")
            await asyncio.sleep(1)
            return Response(), 200

        # Route for /task
        @self.server.route('/task', methods=['POST'])
        async def task():
            data = request.form
            user_id = data.get('user_id')
            user_name = data.get('user_name')
            channel_id = data.get('channel_id')
            self.send_welcome_message(channel_id, user_id)
            await asyncio.sleep(1)
            return Response(), 200

        # Route for /stats-uptime
        @self.server.route('/stats-uptime', methods=['POST'])
        async def stats_uptime():
            data = request.form
            user_id = data.get('user_id')
            user_name = data.get('user_name')
            channel_id = data.get('channel_id')
            myQuery = {
                'answer':'polo'
            }
            response = requests.get("http://192.168.2.97:5000/stats/uptime", data=myQuery)
            parsed = response.json()
            self.client.chat_postMessage(channel=channel_id, text=f"Reading from response object: {parsed['response']}")
            await asyncio.sleep(1)
            return Response(), 200

        # Route for /add-factoid
        @self.server.route('/add-factoid', methods=['POST'])
        async def add_factoid():
            data = request.form
            user_id = data.get('user_id')
            user_name = data.get('user_name')
            channel_id = data.get('channel_id')
            text = data.get('text')
            list = text.split(" ")
            print(list)
            keyword = ''.join(list[:1])
            factoid = ' '.join(list[1:])
            myQuery = {
                'keyword': keyword,
                'factoid': factoid
            }
            response = requests.post("http://192.168.2.97:5000/factoid/add-factoid", data=myQuery)
            parsed = response.json()
            if not parsed['success']:
                self.client.chat_postMessage(channel=channel_id, text=f"Could not add factoid for key: {keyword}")
            # self.client.chat_postMessage(channel=channel_id, text=f"Reading from response object: {parsed['response']}")
            # self.client.chat_postMessage(channel=channel_id, text=f"Your keyword: {keyword}")
            # self.client.chat_postMessage(channel=channel_id, text=f"Your factoid: {factoid}")
            await asyncio.sleep(1)
            return Response(), 200

        # Route for /return-factoid
        @self.server.route('/return-factoid', methods=['POST'])
        async def return_factoid():
            data = request.form
            user_id = data.get('user_id')
            user_name = data.get('user_name')
            channel_id = data.get('channel_id')
            text = data.get('text')
            list = text.split(" ")
            # print(list)
            keyword = ''.join(list[:1])
            print(keyword)
            myQuery = {
                'keyword': keyword
            }
            response = requests.get("http://192.168.2.97:5000/factoid/return-factoid", data=myQuery)
            parsed = response.json()
            # self.client.chat_postMessage(channel=channel_id, text=f"Reading from response object: {parsed['response']}")
            # self.client.chat_postMessage(channel=channel_id, text=f"Your keyword: {keyword}")
            value = ''.join(parsed['value'])
            self.client.chat_postMessage(channel=channel_id, text=f"{value}")
            await asyncio.sleep(1)
            return Response(), 200

        ### WORK ON THIS NEXT
        @self.server.route('/faq', methods=['POST'])
        async def faq():
            data = request.form
            user_name = data.get('user_name')
            channel_id = data.get('channel_id')
            text = data.get('text')
            list = text.split(" ")

            random_positive = random.randint(0,9)
            random_negative = random.randint(0,4)

            if list[0] == "forget":
                keyword = list[1]
                myQuery = {
                    'keyword': keyword
                }
                response = requests.delete("http://192.168.2.97:5000/factoid/remove-factoid", data=myQuery)
                parsed = response.json()
                if parsed['success'] == True:
                    affirmatives_remove = [
                        f"Okay {user_name}, I've forgotten about '{keyword}'.",
                        f"'{keyword}'? What's that again?",
                        f"Alright {user_name}, I'll forget about '{keyword}'."

                    ]
                    random_positive = random.randint(0,2)
                    self.client.chat_postMessage(channel=channel_id, text=affirmatives_remove[random_positive])
                else:
                    negatives_remove = [
                        f"Sorry {user_name}, something went wrong when I tried to forget about '{keyword}'.",
                        f"I ran into an error while trying to forget about '{keyword}', {user_name}.",
                        f"I tried but couldn't forget about '{keyword}', {user_name}.",
                        f"'{keyword}'? I ran into an issue when I tried to forget that, {user_name}?",
                        f"Something went wrong when I tried to get about '{keyword}', {user_name}."
                    ]
                    self.client.chat_postMessage(channel=channel_id, text=negatives_remove[random_negative])
            else:
                # if there is a question mark at the end of the string return a factoid, else add a factoid
                if search("\?$", text):

                    # extract keyword from string
                    last_word = list[-1]
                    keyword = last_word[:-1]
                    myQuery = {
                        'keyword': keyword
                    }
                    response = requests.get("http://192.168.2.97:5000/factoid/return-factoid", data=myQuery)
                    parsed = response.json()
                    if parsed['query_status']:
                        value = ''.join(parsed['value'])
                        self.client.chat_postMessage(channel=channel_id, text=f"{keyword} {value}")
                    else:
                        negatives_return = [
                            f"Sorry {user_name}, there was nothing in my memory about '{keyword}'.",
                            f"I'm not sure I know anything about '{keyword}', {user_name}.",
                            f"I have no idea about '{keyword}', {user_name}.",
                            f"'{keyword}'? What's that, {user_name}?",
                            f"I don't know what '{keyword}' is, {user_name}."
                        ]
                        self.client.chat_postMessage(channel=channel_id, text=negatives_return[random_negative])
                    await asyncio.sleep(1)
                else:
                    keyword = ''.join(list[:1])
                    factoid = ' '.join(list[1:])
                    myQuery = {
                        'keyword': keyword,
                        'factoid': factoid
                    }
                    response = requests.post("http://192.168.2.97:5000/factoid/add-factoid", data=myQuery)
                    parsed = response.json()
                    if not parsed['success']:
                        negatives_add = [
                            f"I couldn't remember that about '{keyword}', {user_name}.",
                            f"Something went wrong when I tried to remember '{keyword}', {user_name}!",
                            f"I ran into an error when I tried adding '{keyword}' to my knowledge base, {user_name}.",
                            f"There might already be a value for '{keyword}', {user_name}.",
                            f"Unable to remember '{keyword}', maybe try something else {user_name}?"
                        ]
                        self.client.chat_postMessage(channel=channel_id, text=negatives_add[random_negative])
                    else:
                        affirmatives_add = [
                            f"Alright {user_name}, I'll remember '{keyword}'.",
                            f"Got it, {user_name}.",
                            f"Thanks for teaching me about '{keyword}', {user_name}!",
                            f"Roger that, Captain {user_name}.",
                            f"Heard you loud and clear, {user_name}.",
                            f"Okay {user_name}, I'll keep '{keyword}' in mind.",
                            f"Understood, {user_name}.",
                            f"That's interesting, {user_name}! Adding '{keyword}' to my memory.",
                            f"I'm going to remember '{keyword}', just for you {user_name}!",
                            f"Thank you for adding to my knowledge base, {user_name}. I feel smarter already!",
                        ]
                        self.client.chat_postMessage(channel=channel_id, text=affirmatives_add[random_positive])
                    await asyncio.sleep(1)

            return Response(), 200

        # Start bot
        # self.client.chat_postMessage(channel="#general", text="SlackBot reporting for duty!")
        self.server.run()


    def send_welcome_message(self, channel, user):
        welcome = WelcomeMessage(channel, user)
        message = welcome.get_message()
        response = self.client.chat_postMessage(**message)
        welcome.timestamp = response['ts']

        if channel not in self.welcome_messages:
            self.welcome_messages[channel] = {}

        self.welcome_messages[channel][user] = welcome
