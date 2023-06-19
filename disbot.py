#!/usr/bin/env python3
import json
import os

import discord
import requests


class DiscordAnchor(discord.Client):
    def __init__(self, config):
        # Read the config and setup the Discord bot
        self.disbot = config["disbot"]
        self.ircbot = config["ircbot"]
        self.channel = config["dis_channel"]
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)

    # Give some log info
    async def on_ready(self):
        print(f"Logged in as {self.user}")

    async def on_message(self, message):
        # If the message is from the bot itself or another channel not configured
        # Ignore it
        if message.author.bot or str(message.channel.id) != self.channel:
            return

        content = message.content

        if str(message.type) == "MessageType.reply":
            # If the message is a reply, send the original message to IRC too
            # Fetch the original message by ID
            original_message = await message.channel.fetch_message(
                message.reference.message_id
            )

            # Build a API payload with the original message to set context for the reply
            reply = {
                "dest": "reply",
                "author": "replying to-->#",
                "content": f"{original_message.content}",
            }

            # Send to ircbot's API. If you changed the Flask app on ircbot,
            # you'll need to fix this too
            requests.get("http://127.0.0.1:54321/irc", params=reply)

        # Some people (like me) talk with line breaks on Discord
        # Replicate this behavior by splitting the messages into separate payloads
        messages = content.split("\n")

        # Iterate through the list of messages and send them to the API
        for m in messages:
            msg = {
                "dest": "irc",
                "author": f"{message.author.nick}#"
                if message.author.nick
                else message.author,
                "content": m,
            }

            # If you changed ircbot's Flask app, you'll need to change this too
            requests.get("http://127.0.0.1:54321/irc", params=msg)


if __name__ == "__main__":
    # Doesn't matter how or where this bot is installed, find the config file
    path = os.path.dirname(os.path.realpath(__file__))
    with open(f"{path}/config.json", "r") as f:
        config = json.loads(f.read())

    # Instantiate the Discord bot, and start it.
    bot = DiscordAnchor(config)
    bot.run(config["disbot"]["token"])
