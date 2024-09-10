import datetime
import logging
import multiprocessing
import os
import discord
import sqlite3
from collections import namedtuple

from flask import Flask, redirect, render_template, request, session

from scripts.get_bot_guilds import get_bot_guilds
from scripts.send_custom_message import (
    broadcast,
    send_to_server,
    broadcast_embed,
    send_embed_to_server,
)
from scripts.send_dm import create_dm_channel, send_dm

logging.basicConfig(
    filename="web.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config["SECRET_KEY"] = "1qaz2wsx3edc4rfv"


@app.route("/vote-callback", methods=["POST"])
def vote_callback():
    logger.info("hello world")
    word_count = 5

    # Check for correct authorization
    if request.headers.get("Authorization") != "super_secret_password":
        return "Hello World"

    # Fetch the data from the request
    data = request.get_json()
    user_id = int(data["user"])
    type_ = data["type"]
    bot = data["bot"]

    if bot != os.getenv("BOT_ID") or type_ != "upvote":
        return "Not an upvote request"

    # Create a new SQLite connection and cursor within the route
    db = sqlite3.connect("db.sqlite3")
    curr = db.cursor()

    # Query and update the database
    voting_record = curr.execute(
        "SELECT user_id, word_count FROM voting_records WHERE user_id=?", (user_id,)
    ).fetchone()

    if not voting_record:
        curr.execute(
            "INSERT INTO voting_records (user_id, word_count) VALUES (?, ?)",
            (user_id, word_count),
        )
    else:
        curr.execute(
            "UPDATE voting_records SET word_count=? WHERE user_id=?",
            (voting_record[1] + word_count, user_id),
        )

    db.commit()

    # Fetch updated record
    voting_record = curr.execute(
        "SELECT word_count FROM voting_records WHERE user_id=?", (user_id,)
    ).fetchone()

    # Close the cursor and connection
    curr.close()
    db.close()

    # Send DM to the user
    VotingRecord = namedtuple("voting_record", ["user_id", "word_count"])
    voting_record = VotingRecord(user_id, voting_record[0])

    channel_id = create_dm_channel(user_id)
    send_dm(
        channel_id,
        f"Thanks for voting, you'll get double coins 💰 for next {voting_record.word_count} words",
    )

    return "Success"


@app.route("/", methods=["GET"])
def home():
    return render_template("home.html")


@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "GET":
        if not session.get("authenticated") == True:
            return render_template("login.html")
        servers = get_bot_guilds()
        active_members = 0
        server_active_users_map = dict()
        with open("active_members.txt", "+r") as f:
            last_time = datetime.datetime.strptime(
                f.readline().strip(), "%d/%m/%Y, %H:%M:%S"
            )
            if datetime.datetime.now() - last_time < datetime.timedelta(hours=4):
                active_members = int(f.readline().strip())
                line = f.readline()
                while line:
                    line = line.strip()
                    server_id, member_count = line.split(" ")
                    server_active_users_map[server_id] = member_count
                    line = f.readline()
            else:
                conn = sqlite3.connect("db.sqlite3")
                curr = conn.cursor()
                curr.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'users_%';"
                )
                tables = curr.fetchall()

                for table in tables:
                    table_name = table[0]
                    curr.execute(f"SELECT COUNT(*) FROM {table_name};")
                    count = curr.fetchone()[0]
                    server_active_users_map[table_name.split("_")[1]] = count
                    active_members += count

                curr.close()
                conn.close()

                with open("active_members.txt", "w") as f2:
                    f2.write(datetime.datetime.now().strftime("%d/%m/%Y, %H:%M:%S"))
                    f2.write("\n")
                    f2.write(str(active_members))
                    f2.write("\n")
                    for server_id, member_count in list(
                        server_active_users_map.items()
                    ):
                        f2.write(f"{server_id} {member_count}\n")

        for server in servers:
            server["active_members"] = server_active_users_map.get(
                str(server["id"]), "DataNA"
            )

        return render_template(
            "admin.html", servers=servers, active_members=active_members
        )
    elif request.method == "POST":
        data = request.form
        username = data.get("username")
        password = data.get("password")
        if username == "slav" and password == "Konnichiwa@11Hajimimashte@11":
            session["authenticated"] = True
        return redirect("/admin")


@app.route("/send_message", methods=["POST"])
def send_message():
    if session.get("authenticated") != True:
        return redirect("/admin")
    data = request.form
    send_to_server(data.get("message"), data.get("server_id"))
    return redirect("/admin")


@app.route("/broadcast", methods=["POST"])
def broadcast_message():
    if session.get("authenticated") != True:
        return redirect("/admin")
    data = request.form
    message = data.get("broadcast_message")
    multiprocessing.Process(target=broadcast, args=(message,), daemon=False).start()
    return redirect("/admin")


@app.route("/broadcast-embed", methods=["POST"])
def broadcast_embed_():
    if session.get("authenticated") != True:
        return redirect("/admin")
    data = request.form

    embed = discord.Embed(
        title=data.get("title"),
        url="https://gamingrefree.online",
        description=data.get("description"),
        colour=0x1EEB36,
    )

    embed.set_author(
        name="GamingRefree",
        url="https://gamingrefree.online",
        icon_url="https://i.imgur.com/O5rRjUu.png",
    )
    if data.get("image"):
        embed.set_image(url=data.get("image"))

    embed.set_footer(
        text="Made by GamingRefree Inc.", icon_url="https://i.imgur.com/O5rRjUu.png"
    )

    multiprocessing.Process(
        target=broadcast_embed, args=(embed.to_dict(),), daemon=False
    ).start()

    return redirect("/admin")


@app.route("/unicast-embed", methods=["POST"])
def unicast_embed():
    if session.get("authenticated") != True:
        return redirect("/admin")
    data = request.form
    server_id = data.get("server_id")
    embed = discord.Embed(
        title=data.get("title"),
        url="https://gamingrefree.online",
        description=data.get("description"),
        colour=0x1EEB36,
    )

    embed.set_author(
        name="GamingRefree",
        url="https://gamingrefree.online",
        icon_url="https://i.imgur.com/O5rRjUu.png",
    )
    if data.get("image"):
        embed.set_image(url=data.get("image"))

    embed.set_footer(
        text="Made by GamingRefree Inc.", icon_url="https://i.imgur.com/O5rRjUu.png"
    )

    send_embed_to_server(embed.to_dict(), server_id)

    return redirect("/admin")


if __name__ == "__main__":
    app.run(debug=True, port=5000, host="127.0.0.1")
