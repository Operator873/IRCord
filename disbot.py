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

        # If there are @mentions, replace the userid with the nick or name
        if message.mentions:
            content = self.fix_mention(message.mentions, content)

        if (
            message.reference is not None
            and isinstance(message.reference.resolved, discord.Message)
        ):
            original_message = message.reference.resolved

            # Check for mentions and attempt to correct
            if original_message.mentions:
                original_content = original_message.content
                original_content = original_content.replace("<", "").replace(">", "")
                # The referenced message doesn't come with clean nick params
                # so we have to look it up manually. For this, we need the guild id
                guild = self.get_guild(message.guild.id)
                for mention in original_message.mentions:
                    # Actively find the person mentioned in the original message and fix their nick
                    person = await guild.fetch_member(mention.id)
                    original_content = original_content.replace(
                        str(mention.id),
                        person.nick if person.nick else person.name
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
    
    def fix_mention(self, mentions, content):
        for mention in mentions:
            if mention.nick:
                content = content.replace(str(mention.id), mention.nick)
            else:
                content = content.replace(str(mention.id), mention.name)
        
        return content


if __name__ == "__main__":
    # Doesn't matter how or where this bot is installed, find the config file
    path = os.path.dirname(os.path.realpath(__file__))
    with open(f"{path}/config.json", "r") as f:
        config = json.loads(f.read())

    # Instantiate the Discord bot, and start it.
    bot = DiscordAnchor(config)
    bot.run(config["disbot"]["token"])
