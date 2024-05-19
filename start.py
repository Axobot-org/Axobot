#!/usr/bin/env python
#coding=utf-8

# check python version
import sys
py_version = sys.version_info
if py_version.major != 3 or py_version.minor < 11:
    print("You must use at least Python 3.11!", file=sys.stderr)
    sys.exit(1)

import pkg_resources

def check_libs():
    """Check if the required libraries are installed and can be imported"""
    with open("requirements.txt", 'r', encoding="utf-8") as file:
        packages = pkg_resources.parse_requirements(file.readlines())
    pkg_resources.working_set.resolve(packages)


check_libs()

# required to avoid segmentation error - don't ask me why
from nltk import SnowballStemmer # pylint: disable=unused-import

import discord
import asyncio
import time
import json
from random import choice
from fcts import tokens  # pylint: disable=no-name-in-module
from libs.bot_classes import Axobot
from libs.boot_utils import set_beta_logs, setup_start_parser, setup_logger, load_cogs, load_sql_connection

async def main():
    "Load everything and start the bot"
    parser = setup_start_parser()
    args = parser.parse_args()

    log = setup_logger()
    log.info("Starting bot")

    client = Axobot(case_insensitive=True, status=discord.Status('online'))

    async def on_ready():
        print('\nBot connected')
        print("Name:", client.user.name)
        print("ID:", client.user.id)
        if len(client.guilds) < 50:
            guild_names = (x.name for x in client.guilds)
            print("Connected on ["+str(len(client.guilds))+"] "+", ".join(guild_names))
        else:
            print("Connected on "+str(len(client.guilds))+" guilds")
        print(time.strftime("%d/%m  %H:%M:%S"))
        print('------')
        await asyncio.sleep(3)
        with open("status_list.json", 'r', encoding="utf-8") as status_file:
            status_list = json.load(status_file)
        if not client.database_online:
            activity = discord.Activity(type=discord.ActivityType.listening, name=choice(status_list['no-db']))
            await client.change_presence(activity=activity)
        else:
            if client.beta:
                status = choice(status_list['beta'])
            else:
                status = choice(status_list['axobot'])
            await client.change_presence(activity=discord.Game(name=status))
        emb = discord.Embed(description=f"**{client.user.name}** is launching !", color=8311585, timestamp=client.utcnow())
        await client.send_embed(emb)

    load_sql_connection(client)
    if client.database_online:
        client.connect_database_axobot()
    elif len(args.token) < 30:
        client.log.fatal("Invalid bot token")
        return

    if args.token == 'axobot':
        bot_data = tokens.get_token(client, 1048011651145797673)
        token = bot_data["token"]
        client.entity_id = bot_data["entity_id"]
    elif args.token == 'beta':
        bot_data = tokens.get_token(client, 436835675304755200)
        token = bot_data["token"]
        client.entity_id = bot_data["entity_id"]
        client.beta = True
        set_beta_logs()
    elif len(args.token) < 30:
        client.log.fatal("Invalid bot token")
        return
    elif args.entity_id is None:
        client.log.fatal("No entity ID nor preset-token provided")
        return
    else:
        token: str = args.token
        client.entity_id = args.entity_id
    # Events loop
    if not args.event_loop:
        client.internal_loop_enabled = False
    # RSS enabled
    if not args.rss_features:
        client.rss_enabled = False
    if args.count_open_files:
        client.files_count_enabled = True


    client.connect_database_xp()
    client.add_listener(on_ready)

    async with client:
        await load_cogs(client)
        await client.start(token)


if __name__ == "__main__":
    asyncio.run(main())
