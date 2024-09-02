import os

import requests


def get_bot_guilds():
    headers = {"Authorization": f"Bot {os.getenv('BOT_TOKEN')}"}
    url = "https://discord.com/api/v10/users/@me/guilds"

    server_ids_set = set()
    last_id = -1
    result = list()
    api_call_fails = 0

    while api_call_fails < 5:
        if last_id == -1:
            response = requests.get(url, headers=headers)
        else:
            response = requests.get(f"{url}?after={last_id}", headers=headers)

        if response.status_code == 200:
            guilds = response.json()
            if guilds:
                last_id = guilds[-1]["id"]
            if last_id in server_ids_set:
                break
            for guild in guilds:
                server_ids_set.add(guild["id"])
                result.append({"name": guild["name"], "id": guild["id"]})
        else:
            break

    return result
