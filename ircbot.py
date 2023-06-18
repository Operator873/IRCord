#!/usr/bin/env python3
import requests
import threading
import json
import random
import os

from flask import Flask, request
from ib3 import Bot
from ib3.auth import SASL
from ib3.connection import SSL
from ib3.mixins import DisconnectOnError, PingServer
from ib3.nick import Ghost
from irc.client import NickMask, MessageTooLong
from waitress import serve


class IRCAnchor(SASL, SSL, DisconnectOnError, PingServer, Ghost, Bot):
    def __init__(self, config):
        self.channel = config['irc_channel']
        self.server = config['server']
        self.bot = config['ircbot']
        self.webhook = config['disbot']['webhook']

        super().__init__(
            server_list=[(self.server['url'], self.server['port'])],
            nickname=self.bot['nick'],
            realname=self.bot['name'],
            ident_password=self.bot['pass'],
            channels=[self.channel],
            max_pings=2,
            ping_interval=300,
        )

        self.users = dict()
    
    def no_ping(self, name):
        return f"{name[:4]}\u200B{name[4:]}"
    
    def send_msg(self, message, target=None):
        if not target:
            target = self.channel
        
        try:        
            nick, msg = message.split(":", 1)
        
            if nick not in self.users:
                self.users[nick] = f"{random.randint(2, 15)}{nick}"
            
            formatted_msg = f"{self.no_ping(self.users[nick])}:{msg}"
        except ValueError:
            formatted_msg = message
        
        try:
            self.connection.privmsg(target, formatted_msg)
        except MessageTooLong:
            self.connection.privmsg(target, formatted_msg[:300])        
    
    def get_nick(self, mask):
        return NickMask(mask).nick
    
    def on_ctcp(self, conn, event):
        if event.arguments[0] == "VERSION":
            conn.ctcp_reply(
                self.get_nick(event.source),
                "Bot for assistng Wikimedia Stewards in ##stew",
            )
        elif event.arguments[0] == "PING" and len(event.arguments) > 1:
            conn.ctcp_reply(self.get_nick(event.source), "PING " + event.arguments[1])

    def on_privmsg(self, conn, event):
        nick = self.get_nick(event.source)
        self.send_msg("Hi! I'm a bot and don't answer PMs.", nick)
        
    def on_action(self, conn, event):
        content = event.arguments[0]
        nick = event.source.nick

        if (
            not self.has_primary_nick()
            or nick == self.bot['nick']
        ):
            return
        
        msg = {
            "embeds": [{
                "author": {
                    "icon_url": "https://873gear.com/Stew_Bridge.png"
                },
                "description": f"*{nick} {content}*",
                "color": 1127128
            }]
        }

        result = requests.post(self.webhook, json=msg)
        if not result.ok:
            print(result.json())
    
    def on_pubmsg(self, conn, event):
        content = event.arguments[0]
        nick = event.source.nick

        if (
            not self.has_primary_nick()
            or nick == self.bot['nick']
        ):
            return
        
        msg = {
            "username": nick,
            "avatar_url": "https://873gear.com/Stew_Bridge.png",
            "content": content
        }

        result = requests.post(self.webhook, json=msg)
        if not result.ok:
            print(result.json())


class BotThread(threading.Thread):
    def __init__(self, bot):
        threading.Thread.__init__(self)
        self.b = bot

    def run(self):
        self.b.start()


app = Flask(__name__)

@app.route("/irc", methods=['GET'])
def handle_msg():
    if request.args.get("author") == bot.bot['nick']:
        return

    if request.args.get("dest") == "irc":
        author, _drop= request.args.get("author").split('#', 1)
        bot.send_msg(f"""{author}: {request.args.get("content")}""")
    
    elif request.args.get("dest") == "reply":
        author, _drop= request.args.get("author").split('#', 1)
        bot.send_msg(f"""{author} {request.args.get("content")}""")
    
    else:
        return "ERROR", 406

    return "OK", 200

if __name__ == "__main__":
    path = os.path.dirname(os.path.realpath(__file__))
    with open(f"{path}/config.json", "r") as f:
        config = json.loads(f.read())
    bot = IRCAnchor(config)

    try:
        ircbot = BotThread(bot)

        ircbot.start()
        serve(app, host="0.0.0.0", port=54321)
    except KeyboardInterrupt:
        bot.send_msg("Killed by a KeyboardInterrupt")
        bot.disconnect("Killed by a KeyboardInterrupt")
    except Exception:
        bot.disconnect("StewardBot encountered an unhandled exception")
    finally:
        # no matter how something failed, just get out of here
        raise SystemExit()