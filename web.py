import os
from flask import Flask, request, render_template_string
from scripts.send_dm import create_dm_channel, send_dm
import logging
import sqlite3
from collections import namedtuple

logger = logging.getLogger(__name__)

app = Flask(__name__)


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
        f"Thanks for voting, you'll get double points for next {voting_record.word_count} words",
    )

    return "Success"


@app.route("/", methods=["GET"])
def home():
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Wordchain Bot - GamingRefree</title>
        <style>
            body {
                font-family: 'Arial', sans-serif;
                background-color: #1e1e2f;
                color: #f0f0f0;
                margin: 0;
                padding: 0;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
            }
            .container {
                background-color: #2e2e3e;
                border-radius: 12px;
                padding: 40px;
                max-width: 800px;
                text-align: center;
                box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.5);
            }
            h1 {
                color: #ff9900;
                font-size: 48px;
                margin-bottom: 20px;
            }
            p {
                line-height: 1.6;
                font-size: 18px;
                margin-bottom: 10px;
            }
            .rules, .commands {
                background-color: #3e3e4f;
                padding: 20px;
                border-radius: 8px;
                margin-bottom: 20px;
            }
            .commands {
                display: flex;
                justify-content: space-around;
                flex-wrap: wrap;
            }
            .command-section {
                margin-bottom: 20px;
            }
            .command-section h3 {
                color: #ffcc00;
                font-size: 24px;
                margin-bottom: 10px;
            }
            code {
                background-color: #1e1e2f;
                padding: 5px 10px;
                border-radius: 5px;
                font-size: 16px;
                display: block;
                color: #ffcc00;
            }
            .buttons {
                margin-top: 30px;
                display: flex;
                justify-content: center;
                gap: 20px;
            }
            .btn {
                padding: 15px 30px;
                font-size: 18px;
                font-weight: bold;
                border-radius: 8px;
                border: none;
                cursor: pointer;
                text-transform: uppercase;
                transition: background-color 0.3s;
            }
            .btn-invite {
                background-color: #ff5722;
                color: white;
            }
            .btn-invite:hover {
                background-color: #e64a19;
            }
            .btn-support {
                background-color: #007bff;
                color: white;
            }
            .btn-support:hover {
                background-color: #0056b3;
            }
            a {
                text-decoration: none;
                color: inherit;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>GamingRefree Wordchain Bot</h1>
            <p>Welcome to the official homepage of the Wordchain Discord Bot, where every word counts!</p>
            <div class="rules">
                <h2>Wordchain Rules</h2>
                <p>1. Check the previous accepted word.</p>
                <p>2. Using the last letter of that write a new word.</p>
                <p>3. NO CONSECUTIVE TURNS ALLOWED.</p>
                <p>4. 7 or more characters in the word = 6 points.</p>
                <p>5. 6 or lesser characters in the word = 4 points.</p>
                <p>6. Same starting and ending letter = Additional 2 points.</p>
                <p>7. Out of turn, wrong word in the chain = 2 points will be deducted.</p>
                <p>8. Word length has to be greater than 3.</p>
            </div>
            <div class="buttons">
                <a href="https://top.gg/bot/1225490759432798320/vote" target="_blank">
                    <button class="btn btn-support">Vote - Get 2x Points</button>
                </a>
                <a href="https://discord.com/oauth2/authorize?client_id=1225490759432798320&scope=bot" target="_blank">
                    <button class="btn btn-invite">Invite Bot</button>
                </a>
                <a href="https://discord.gg/BAnFejS7bQ" target="_blank">
                    <button class="btn btn-support">Join Support Server</button>
                </a>
            </div>
            <br />
            <div class="commands">
                <div class="command-section">
                    <h3>User Commands</h3>
                    <code>@GamingRefree myscore</code>
                    <code>@GamingRefree score</code>
                    <code>@GamingRefree meaning &lt;word&gt;</code>
                </div>
                <div class="command-section">
                    <h3>Slash Commands</h3>
                    <code>/vote - Get double points for next 5 words</code>
                    <code>/global_leaderboard - Get global rankings</code>
                </div>
                <div class="command-section">
                    <h3>Admin Commands</h3>
                    <code>@GamingRefree activate</code>
                    <code>@GamingRefree deactivate</code>
                    <code>@GamingRefree exhaust &lt;letter&gt;</code>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return render_template_string(html_content)


if __name__ == "__main__":
    app.run(debug=True, port=5000, host="127.0.0.1")
