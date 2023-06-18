#!/usr/bin/env python3
import discord
import requests
import json
import os

class DiscordAnchor(discord.Client):
    def __init__(self, config):
        self.disbot = config['disbot']
        self.ircbot = config['ircbot']
        self.channel = config['dis_channel']
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
    
    async def on_ready(self):
        print(f"Logged in as {self.user}")
    
    async def on_message(self, message):
        if (
            message.author.bot
            or str(message.channel.id) != self.channel
        ):
            return

        content = message.content
        
        if str(message.type) == "MessageType.reply":
            original_message = await message.channel.fetch_message(message.reference.message_id)

            reply = {
                "dest": "reply",
                "author": "replying to-->#",
                "content": f"{original_message.content}"
            }

            requests.get("http://127.0.0.1:54321/irc", params=reply)

        messages = content.split("\n")

        for m in messages:
            msg = {
                "dest": "irc",
                "author": f"{message.author.nick}#" if message.author.nick else message.author,
                "content": m
            }

            requests.get("http://127.0.0.1:54321/irc", params=msg)

if __name__ == "__main__":
    path = os.path.dirname(os.path.realpath(__file__))
    with open(f"{path}/config.json", "r") as f:
        config = json.loads(f.read())

    bot = DiscordAnchor(config)
    bot.run(config['disbot']['token'])