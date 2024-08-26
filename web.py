import os
from flask import Flask, request, render_template, session, redirect
from scripts.send_dm import create_dm_channel, send_dm
from scripts.get_bot_guilds import get_bot_guilds
from scripts.send_custom_message import send_to_server, broadcast
import logging
import sqlite3
from collections import namedtuple
import multiprocessing

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
        return render_template("admin.html", servers=servers)
    elif request.method == "POST":
        data = request.form
        username = data.get("username")
        password = data.get("password")
        if username == "slav" and password == "slavoid":
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
    broadcast(data.get("broadcast_message"))
    return redirect("/admin")


if __name__ == "__main__":
    app.run(debug=True, port=5000, host="127.0.0.1")
