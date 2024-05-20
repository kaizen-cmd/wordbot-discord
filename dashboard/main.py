from flask import Flask, request, render_template, session
import requests
import os

app = Flask(__name__)

headers = {
    "Authorization": f'Bot {os.getenv("BOT_TOKEN")}',
    "Content-Type": "application/json",
}


@app.route("/", methods=["GET", "POST"])
def home():
    global headers
    if request.method == "GET":
        if session.get("username") == "slav":
            response = requests.get(
                "https://discord.com/api/v9/users/@me/guilds", headers=headers
            )
            servers = response.json()
            return render_template(
                "dashboard.html", servers=[server["name"] for server in servers]
            )
        else:
            return render_template("login.html")
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == "slav" and password == "salvador12345":
            session["username"] = username
            return render_template("dashboard.html")
        return render_template("login.html")


@app.route("/dashboard", methods=["POST"])
def dashboard():
    if request.method == "POST" and session.get("username") == "slav":
        server_id = 1240898515555844127
        channel_id = 1240898515555844130
        message = request.form.get("message")
        data = {"content": message}
        response = requests.post(
            f"https://discord.com/api/v9/channels/{channel_id}/messages",
            headers=headers,
            json=data,
        )
        if response.status_code == 200:
            print(f"Message sent to channel {channel_id} in guild {server_id}")
        else:
            print(
                f"Failed to send message to channel {channel_id} in guild {server_id}. Status code: {response.status_code}"
            )
        return render_template("dashboard.html", context={"message": message})


app.secret_key = "some_super_secret_key"
app.run(debug=True, host="0.0.0.0", port=8081)
