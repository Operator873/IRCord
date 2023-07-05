#!/usr/bin/env python3
import json
import os
import random
import threading

import requests
from flask import Flask, request
from ib3 import Bot
from ib3.auth import SASL
from ib3.connection import SSL
from ib3.mixins import DisconnectOnError, PingServer
from ib3.nick import Ghost
from irc.client import MessageTooLong, NickMask
from waitress import serve


class IRCAnchor(SASL, SSL, DisconnectOnError, PingServer, Ghost, Bot):
    def __init__(self, config):
        # Set some options from the config
        self.channel = config["irc_channel"]
        self.server = config["server"]
        self.bot = config["ircbot"]
        self.webhook = config["disbot"]["webhook"]

        # Configure the IRC bot connection
        super().__init__(
            server_list=[(self.server["url"], self.server["port"])],
            nickname=self.bot["nick"],
            realname=self.bot["name"],
            ident_password=self.bot["pass"],
            channels=[self.channel],
            max_pings=2,
            ping_interval=300,
        )

        # Initialize a dictionary for using with nick colors
        self.users = dict()

    def no_ping(self, name):
        # Add a zero width space to Discord nicks to prevent pings on IRC
        return f"{name[:4]}\u200B{name[4:]}"
    
    def on_quit(self, conn, event):
        quit_message = event.arguements['0']

        # Build the webhook payload
        msg = {
            "avatar_url": "https://873gear.com/Stew_Bridge.png",
            "content": f"*{event.source.nick} has {event.type} {quit_message}*",
        }

        # Send the payload and casually check for okness
        result = requests.post(self.webhook, json=msg)
        if not result.ok:
            print(result.json())


    def on_join(self, conn, event):
        # If the bot doesn't have its nick or if the message is from the bot
        # Ignore it
        if not self.has_primary_nick() or event.source.nick == self.bot["nick"]:
            return
        else:
            self.alfred_handle(event)
    
    def on_part(self, conn, event):
        # If the bot doesn't have its nick or if the message is from the bot
        # Ignore it
        if not self.has_primary_nick() or event.source.nick == self.bot["nick"]:
            return
        else:
            self.alfred_handle(event)

    def alfred_handle(self, event):
        # Build the webhook payload
        msg = {
            "avatar_url": "https://873gear.com/Stew_Bridge.png",
            "content": f"*{event.source.nick} has {event.type}ed {event.target}*",
        }

        # Send the payload and casually check for okness
        result = requests.post(self.webhook, json=msg)
        if not result.ok:
            print(result.json())

    def send_msg(self, message, target=None):
        # If a target is explicit, use it, else default config channel
        target = target if target else self.channel
        nick, msg = message.split(":", 1)

        # Check the local dict for the user. If not exist, make a pretty random color
        if nick not in self.users:
            # Set an int which translates to color on IRC
            color = random.randint(2, 15)
            
            # Nobody likes yellow, pick again until we have something else
            while color == 8:
                color = random.randint(2, 15)
            
            # Save the pretty color in the temp dict
            self.users[nick] = f"{color}{nick}"

        # Format the message so it doesn't ping AND is pretty colored
        formatted_msg = f"{self.no_ping(self.users[nick])}:{msg}"

        # Try to send the message to the IRC server
        # Catch Message too long errors, and just trim and discard
        # Mainly because I'm lazy
        try:
            self.connection.privmsg(target, formatted_msg)
        except MessageTooLong:
            self.connection.privmsg(target, formatted_msg[:300])

    def get_nick(self, mask):
        # Convert a hostmask into just a nick
        return NickMask(mask).nick

    def on_ctcp(self, conn, event):
        # Answer VERSION requests. This is sometimes done on serverside
        if event.arguments[0] == "VERSION":
            conn.ctcp_reply(
                self.get_nick(event.source),
                "Bot for assistng Wikimedia Stewards in ##stew",
            )
        elif event.arguments[0] == "PING" and len(event.arguments) > 1:
            # Answer PING events via CTCP. Not the same as server pings
            conn.ctcp_reply(self.get_nick(event.source), "PING " + event.arguments[1])

    def on_privmsg(self, conn, event):
        # There's no need for PMs with this bot, but be polite about it
        nick = self.get_nick(event.source)
        self.send_msg("Hi! I'm a bot and don't answer PMs.", nick)

    def on_action(self, conn, event):
        # Process an /me action event on IRC and send to webhook
        content = event.arguments[0]
        nick = event.source.nick

        # If the bot doesn't have it's nick or if the message is from the bot
        # Ignore it
        if not self.has_primary_nick() or nick == self.bot["nick"]:
            return

        # Build the webhook payload
        msg = {
            "embeds": [
                {
                    "author": {"icon_url": "https://873gear.com/Stew_Bridge.png"},
                    "description": f"*{nick} {content}*",
                    "color": 1127128,
                }
            ]
        }

        # Send to the webhook, check for success. If not, write to syslog
        result = requests.post(self.webhook, json=msg)
        if not result.ok:
            print(result.json())

    def on_pubmsg(self, conn, event):
        # Process any message event in the channel the bot occupies
        content = event.arguments[0]
        nick = event.source.nick

        # If the bot doesn't have its nick or if the message is from the bot
        # Ignore it
        if not self.has_primary_nick() or nick == self.bot["nick"]:
            return

        # Build the webhook payload
        msg = {
            "username": nick,
            "avatar_url": "https://873gear.com/Stew_Bridge.png",
            "content": content,
        }

        # Send the payload and casually check for okness
        result = requests.post(self.webhook, json=msg)
        if not result.ok:
            print(result.json())


class BotThread(threading.Thread):
    # Wrapper for threading
    def __init__(self, bot):
        threading.Thread.__init__(self)
        self.b = bot

    def run(self):
        self.b.start()


# API endpoint for Discord bot
app = Flask(__name__)


# The /irc portion can be changed to whatever you want
# so long as you change the disbot.py API message target too
@app.route("/irc", methods=["GET"])
def handle_msg():
    # If, somehow, the bot's message made it this far, ignore it now
    if request.args.get("author") == bot.bot["nick"]:
        return

    # There are two different API requests, an regular message, and a reply
    if request.args.get("dest") == "irc":
        # Regular messages only have the author and message content
        author, _drop = request.args.get("author").split("#", 1)
        bot.send_msg(f"""{author}: {request.args.get("content")}""")

    elif request.args.get("dest") == "reply":
        # Replies substitue the "author" for a reply-to--> instead
        author, _drop = request.args.get("author").split("#", 1)
        bot.send_msg(f"""{author} {request.args.get("content")}""")

    else:
        # Anything else, send back Not Acceptable because why not
        return "ERROR", 406

    return "OK", 200


if __name__ == "__main__":
    # Doesn't matter how or where the script is running
    # look for the config file there.
    path = os.path.dirname(os.path.realpath(__file__))
    with open(f"{path}/config.json", "r") as f:
        # Read the config and pass it to the bot
        config = json.loads(f.read())
    bot = IRCAnchor(config)

    try:
        # Put the bot in a thread
        ircbot = BotThread(bot)
        # Start the Thread
        ircbot.start()
        # Start the API endpoint
        serve(app, host="0.0.0.0", port=54321)
    except KeyboardInterrupt:
        # Handle interrupts
        bot.send_msg("Killed by a KeyboardInterrupt")
        bot.disconnect("Killed by a KeyboardInterrupt")
    except Exception:
        # Handle Operator873 mistakes
        bot.disconnect("StewardBot encountered an unhandled exception")
    finally:
        # no matter how something failed, just get out of here
        raise SystemExit()
