import json
import os

import requests


def get_bot_guilds(servers=None):
    headers = {"Authorization": f"Bot {os.getenv('BOT_TOKEN')}"}
    url = "https://discord.com/api/v10/users/@me/guilds?with_counts=true"

    activated_servers_map = dict()
    with open("server_channel_mapping.json", "r") as f:
        activated_servers_map = json.loads(f.read())

    server_ids_set = set()
    last_id = -1
    result = list()
    api_call_fails = 0
    response = None
    server_count = 0
    while api_call_fails < 5 and (not servers or server_count < servers):
        if last_id == -1:
            try:
                response = requests.get(url, headers=headers)
            except:
                api_call_fails += 1
                continue
        else:
            try:
                response = requests.get(f"{url}&after={last_id}", headers=headers)
            except:
                api_call_fails += 1
                continue

        if response and response.status_code == 200:
            guilds = response.json()
            if guilds:
                last_id = guilds[-1]["id"]
            if last_id in server_ids_set:
                break
            for guild in guilds:
                server_ids_set.add(guild["id"])
                activation_status = (
                    True if activated_servers_map.get(str(guild["id"])) else False
                )
                result.append(
                    {
                        "name": guild["name"],
                        "id": guild["id"],
                        "member_count": guild["approximate_member_count"],
                        "activation_status": activation_status,
                        "icons": guild["icon"],
                    }
                )
                server_count += 1
        else:
            break

    return result
