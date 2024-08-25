import requests
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")


def create_dm_channel(user_id):
    user_id = int(user_id)
    url = "https://discord.com/api/v9/users/@me/channels"
    headers = {"Authorization": f"Bot {BOT_TOKEN}", "Content-Type": "application/json"}
    data = {"recipient_id": user_id}
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()  # Ensure we catch any errors
    return response.json()["id"]


def send_dm(channel_id, message):
    channel_id = int(channel_id)
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
    headers = {"Authorization": f"Bot {BOT_TOKEN}", "Content-Type": "application/json"}
    data = {"content": message}
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()
