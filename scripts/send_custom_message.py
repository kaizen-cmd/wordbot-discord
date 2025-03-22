"""
CLI Usage
python send_custom_message.py broadcast --message "Your message here"
python send_custom_message.py single --message "Your message here" --server SERVER_ID
"""

import argparse
import json
import logging
import os
import time

import requests

logging.basicConfig(
    filename="logs/web.log",
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

f = open("./server_channel_mapping.json", "r")
server_channel_mapping = json.loads(f.read())
f.close()
headers = {
    "Authorization": f'Bot {os.getenv("BOT_TOKEN")}',
    "Content-Type": "application/json",
}


def send_to_server(message="Hello World!", server_id="1234116258186657872"):
    global server_channel_mapping
    global headers
    channel_id = server_channel_mapping.get(server_id)
    if channel_id:
        data = {"content": message}
        response = requests.post(
            f"https://discord.com/api/v9/channels/{channel_id}/messages",
            headers=headers,
            json=data,
        )
        if response.status_code == 200:
            print(f"Message sent to channel {channel_id} in guild {server_id}")
        else:
            print(
                f"Failed to send message to channel {channel_id} in guild {server_id}. Status code: {response.status_code}"
            )


def send_embed_to_server(message="Hello World!", server_id="1234116258186657872"):
    global server_channel_mapping
    global headers
    channel_id = server_channel_mapping.get(server_id)
    if channel_id:
        data = {"embed": message}
        response = requests.post(
            f"https://discord.com/api/v9/channels/{channel_id}/messages",
            headers=headers,
            json=data,
        )
        if response.status_code == 200:
            print(f"Message sent to channel {channel_id} in guild {server_id}")
        else:
            print(
                f"Failed to send message to channel {channel_id} in guild {server_id}. Status code: {response.status_code}"
            )


def broadcast(message="Hello!"):
    logger = logging.getLogger("broadcast_message_log")
    global server_channel_mapping
    global headers
    response = requests.get(
        "https://discord.com/api/v9/users/@me/guilds", headers=headers
    )
    servers = response.json()
    for server in servers:
        server_id = server["id"]
        channel_id = server_channel_mapping.get(server_id)
        if channel_id:
            data = {"content": message}

            response = requests.post(
                f"https://discord.com/api/v9/channels/{channel_id}/messages",
                headers=headers,
                json=data,
            )

            if response.status_code == 200:
                logger.info(
                    f"Message sent to channel {channel_id} in guild {server['name']}"
                )
            else:
                logger.error(
                    f"Failed to send message to channel {channel_id} in guild {server_id}. Status code: {response.status_code}"
                )


def broadcast_embed(message="Hello!"):
    global server_channel_mapping
    global headers
    server_count = 0
    success_server_count = 0
    data = {"embeds": [message]}
    title = data["embeds"][0]["title"]
    sent_ids = []
    for server_id, channel_id in server_channel_mapping.items():
        response = requests.post(
            f"https://discord.com/api/v9/channels/{channel_id}/messages",
            headers=headers,
            json=data,
        )
        logger.info(
            f"#{server_count} Broadcast Embed Status {server_id}: {response.status_code}"
        )
        server_count += 1
        if response.status_code == 200:
            json_response = response.json()
            id = json_response["id"]
            sent_ids.append([channel_id, id])
            success_server_count += 1
        time.sleep(1)
    existing_sent_ids = {}
    with open("sent_ids.json", "r") as f:
        existing_sent_ids = json.loads(f.read())
    with open("sent_ids.json", "w") as f:
        existing_sent_ids[title] = sent_ids
        f.write(json.dumps(existing_sent_ids))
    logger.info(
        f"Broadcasted embed stat {success_server_count}/{len(server_channel_mapping)}, {success_server_count/len(server_channel_mapping)*100}%"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send messages to Discord servers")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    broadcast_parser = subparsers.add_parser(
        "broadcast", help="Broadcast message to all servers"
    )
    broadcast_parser.add_argument(
        "--message",
        "-m",
        default="Hello!",
        help="Message to be broadcasted (default: Hello!)",
    )

    single_server_parser = subparsers.add_parser(
        "single", help="Send message to a single server"
    )
    single_server_parser.add_argument(
        "--message",
        "-m",
        default="# Developer needs your support 😄\nIf you feel this bot is fun please upvote here ⬆️\nhttps://discordbotlist.com/bots/wordchainadmin",
        help="Message to be sent (default: Hello!)",
    )
    single_server_parser.add_argument(
        "--server",
        "-s",
        default="1234116258186657872",
        help="ID of the server to send message to (default: 1234116258186657872)",
    )

    args = parser.parse_args()

    if args.command == "broadcast":
        broadcast(args.message)
    elif args.command == "single":
        send_to_server(args.message, args.server)
