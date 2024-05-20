from flask import Flask, request, render_template, session, redirect, url_for, flash
import requests
import os

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "default_secret_key")

DISCORD_API_URL = "https://discord.com/api/v9"
BOT_TOKEN = os.getenv("BOT_TOKEN")
HEADERS = {
    "Authorization": f"Bot {BOT_TOKEN}",
    "Content-Type": "application/json",
}


@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "GET":
        if session.get("username") == "slav":
            response = requests.get(
                f"{DISCORD_API_URL}/users/@me/guilds", headers=HEADERS
            )
            if response.status_code == 200:
                servers = response.json()
                return render_template("dashboard.html", servers=servers)
            else:
                flash("Failed to fetch server information.", "error")
                return redirect(url_for("login"))
        else:
            return redirect(url_for("login"))

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == "slav" and password == "salvador12345":
            session["username"] = username
            return redirect(url_for("home"))
        else:
            flash("Invalid username or password.", "error")
            return redirect(url_for("login"))


@app.route("/login", methods=["GET"])
def login():
    return render_template("login.html")


@app.route("/dashboard", methods=["POST"])
def dashboard():
    if session.get("username") == "slav":
        server_id = 1240898515555844127
        channel_id = 1240898515555844130
        message = request.form.get("message")
        data = {"content": message}
        response = requests.post(
            f"{DISCORD_API_URL}/channels/{channel_id}/messages",
            headers=HEADERS,
            json=data,
        )
        if response.status_code == 200:
            flash(
                f"Message sent to channel {channel_id} in guild {server_id}.", "success"
            )
        else:
            flash(
                f"Failed to send message. Status code: {response.status_code}", "error"
            )
        return redirect(url_for("home"))
    else:
        flash("Unauthorized access.", "error")
        return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8081)
