# IRCord
This is an easy-to-use and easy-to-understand pure Python IRC-Discord bridge. It's probably not the easiest way to do it, but it was fun to build and tinker with. There are currently no !commands on either IRC or Discord, but some are planned in the future.

## Overview
### Requirements
The `requirements` file contains a list of library requirements for both boths. After you clone the repo, you can run `pip3 install -r requirements` from within the directory and verify you have everything you need.

In addition, you'll need to create a Discord bot. The easiest guide for this is the discord library doc page found [here](https://discordpy.readthedocs.io/en/stable/discord.html). The bot token will need to be added to `config.json`.

Finally, on your Discord server, you'll need to generate a webhook URL. This is fairly straightforward and easy to do. The webhook URL will need to be added to `config.json` as well.

### ircbot.py
The IRC bot is built with ib3 library. The bot uses the Discord webhook currently to send message payloads to Discord. This is likely not the best way to do it, but I had a lot of issues trying to get the IRC bot and the Discord bot to communicate across intances. For now, this will do and do nicely.

The ircbot also listens on the local machine for incoming JSON payloads sent by the Discord bot. The default is port 54321 and it's currently written to listen on `0.0.0.0` which is any available interface. You might want to consider changing it to `127.0.0.1` if you are not running it behind a firewall.

### disbot.py
This is the Discord bot built using the Python discord library. Instead of the bot method, I elected to use the Client for now. In the furture, I might change that to bot and rework it for certain benefits. Messages in the bot's configured channel will be added to a JSON payload and sent to ircbot listening via the Flask API endpoint.

### config.json
I did not build any sanity checking into either bot. If you do not configure your bot, you'll attempt to connecto Libera IRC servers with all the fake details. Do this too many times and Librea may end up blocking you. Don't do that. Instead, DO complete the configuration prior to launching the bots.

## Methods
### Systemd
This is my preferred method. To create a service, create a file called ircord-discord.service with something like the following content. For the example, I'll just use disbot.py, but you'll need a systemd service for both bots.
```
[Unit]
Description=The Discord side of IRCord Bridge
After=multi-user.target

[Service]
Type=simple
Restart=always
ExecStart=/usr/bin/python3 /path/to/IRCord/disbot.py
# Change the above path to match your situation.

[Install]
WantedBy=multi-user.target
```

I prefer using a non-privileged automation account and creating these services as a systemd `--user` process. That has a bit more setup involved, so you do what's best for you.

If you want to use the systemd `--user` method, put the file into your `~/.config/systemd/user` directory, then do `systemctl --user daemon-reload` to sync systemd. Once both services are created (one for disbot.py and another for ircbot.py), you'll be able to start the bots with `systemctl --user enable --now ircord-discord.service` and systemd will mind and restart them for you. Log information will be in `/var/log/messages`.

### Direct
You can run these bots directly on the command line by calling them directly. Examples:  
- `python3 /path/to/IRCord/disbot.py`  
- `/path/to/IRCord/disbot.py`

