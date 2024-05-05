import os
import requests
import sqlite3
import json

conn = sqlite3.connect("db.sqlite3")
curr = conn.cursor()

f = open("./server_channel_mapping.json", "r")
server_channel_mapping = json.loads(f.read())
f.close()
headers = {
    "Authorization": f'Bot {os.getenv("BOT_TOKEN")}',
    "Content-Type": "application/json",
}


def get_users_table_name(server_id):
    return f"users_{server_id}"


def get_words_table_name(server_id):
    return f"words_{server_id}"


def get_last_char_user_table_name(server_id):
    return f"lcu_{server_id}"


def deboard_servers():
    global server_channel_mapping
    global curr
    headers = {"Authorization": f'Bot {os.getenv("BOT_TOKEN")}'}
    response = requests.get(
        "https://discord.com/api/v9/users/@me/guilds", headers=headers
    )
    servers = response.json()
    for server in servers:
        server_id = server["id"]
        url = f"https://discord.com/api/v9/guilds/{server_id}"
        response = requests.get(url, headers=headers)
        data = response.json()
        server_name = data["name"]
        answer = input(f"Deboard server {server_name} ? Y/N : ")
        if answer == "Y":
            user_table = get_users_table_name(server_id)
            word_table = get_words_table_name(server_id)
            last_char_user_table = get_last_char_user_table_name(server_id)

            curr.execute(f"DROP TABLE IF EXISTS {word_table}")
            curr.execute(f"DROP TABLE IF EXISTS {user_table}")
            curr.execute(f"DROP TABLE IF EXISTS {last_char_user_table}")
            conn.commit()
            print(f"De boarded server {server_id}")


if __name__ == "__main__":
    deboard_servers()
    curr.close()
    conn.close()
