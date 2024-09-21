import os

import requests

headers = {"Authorization": f"Bot {os.getenv('BOT_TOKEN')}"}
url = "https://discord.com/api/v10/users/@me/guilds?with_counts=true"

response = requests.get(url, headers=headers)
guilds = response.json()

# https://cdn.discordapp.com/icons/1246786555851571354/08be72499ba274e4ec001dea67299743.webp?size=128
servers = 40

for guild in guilds:
    if not servers:
        break
    if servers < 20:
        print(
            f"""
            <div class="logo">
                <img src="https://cdn.discordapp.com/icons/{guild["id"]}/{guild["icon"]}.webp?size=256" alt="" />
            </div>
    """
        )
    servers -= 1
