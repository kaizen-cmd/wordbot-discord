import requests
import os


def get_bot_guilds():
    url = "https://discord.com/api/v10/users/@me/guilds"
    headers = {"Authorization": f"Bot {os.getenv('BOT_TOKEN')}"}

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        guilds = response.json()
        # Extract the server name and server ID
        return [{"name": guild["name"], "id": guild["id"]} for guild in guilds]
    else:
        print(f"Failed to fetch guilds: {response.status_code}, {response.text}")
        return []
