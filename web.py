import datetime
import logging
import multiprocessing
import os
import discord
import sqlite3
from collections import namedtuple
from fastapi import FastAPI, Request, Form, WebSocketDisconnect
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request
from fastapi.staticfiles import StaticFiles
from fastapi import WebSocket
import asyncio

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

app = FastAPI()

# Add session middleware for managing sessions
app.add_middleware(SessionMiddleware, secret_key="1qaz2wsx3edc4rfv")

# Set up templates
templates = Jinja2Templates(directory="templates")

# mount static files
app.mount("/static/", StaticFiles(directory="static"), name="static")


@app.post("/vote-callback")
async def vote_callback(request: Request):
    logger.info("hello world")
    word_count = 5

    # Check for correct authorization
    if request.headers.get("Authorization") != "super_secret_password":
        return "Hello World"

    # Fetch the data from the request
    data = await request.json()
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


@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})


@app.get("/admin")
async def admin_get(request: Request):
    if not request.session.get("authenticated"):
        return templates.TemplateResponse("login.html", {"request": request})

    servers = get_bot_guilds()
    active_members = 0
    server_active_users_map = dict()

    try:
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
    except FileNotFoundError:
        pass

    for server in servers:
        server["active_members"] = server_active_users_map.get(
            str(server["id"]), "DataNA"
        )

    return templates.TemplateResponse(
        "admin.html",
        {"request": request, "servers": servers, "active_members": active_members},
    )


@app.post("/admin")
async def admin_post(
    request: Request, username: str = Form(...), password: str = Form(...)
):
    if username == "slav" and password == "Konnichiwa@11Hajimimashte@11":
        request.session["authenticated"] = True
    return RedirectResponse("/admin", status_code=303)


@app.post("/send_message")
async def send_message(
    request: Request, message: str = Form(...), server_id: str = Form(...)
):
    if request.session.get("authenticated") != True:
        return RedirectResponse("/admin", status_code=303)
    send_to_server(message, server_id)
    return RedirectResponse("/admin", status_code=303)


@app.post("/broadcast")
async def broadcast_message(request: Request, broadcast_message: str = Form(...)):
    if request.session.get("authenticated") != True:
        return RedirectResponse("/admin", status_code=303)
    multiprocessing.Process(
        target=broadcast, args=(broadcast_message,), daemon=False
    ).start()
    return RedirectResponse("/admin", status_code=303)


@app.post("/broadcast-embed")
async def broadcast_embed_(
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    image: str = Form(None),
):
    if request.session.get("authenticated") != True:
        return RedirectResponse("/admin", status_code=303)

    embed = discord.Embed(
        title=title,
        url="https://gamingrefree.online",
        description=description,
        colour=0x1EEB36,
    )

    embed.set_author(
        name="GamingRefree",
        url="https://gamingrefree.online",
        icon_url="https://i.imgur.com/O5rRjUu.png",
    )
    if image:
        embed.set_image(url=image)

    embed.set_footer(
        text="Made by GamingRefree Inc.", icon_url="https://i.imgur.com/O5rRjUu.png"
    )

    multiprocessing.Process(
        target=broadcast_embed, args=(embed.to_dict(),), daemon=False
    ).start()
    return RedirectResponse("/admin", status_code=303)


@app.post("/unicast-embed")
async def unicast_embed(
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    server_id: str = Form(...),
    image: str = Form(None),
):
    if request.session.get("authenticated") != True:
        return RedirectResponse("/admin", status_code=303)

    embed = discord.Embed(
        title=title,
        url="https://gamingrefree.online",
        description=description,
        colour=0x1EEB36,
    )

    embed.set_author(
        name="GamingRefree",
        url="https://gamingrefree.online",
        icon_url="https://i.imgur.com/O5rRjUu.png",
    )
    if image:
        embed.set_image(url=image)

    embed.set_footer(
        text="Made by GamingRefree Inc.", icon_url="https://i.imgur.com/O5rRjUu.png"
    )

    send_embed_to_server(embed.to_dict(), server_id)
    return RedirectResponse("/admin", status_code=303)


@app.get("/logs")
def logs(request: Request):
    if request.session.get("authenticated") != True:
        return RedirectResponse("/admin", status_code=303)
    return templates.TemplateResponse("log.html", {"request": request})


@app.websocket("/stream-logs")
async def stream_logs(websocket: WebSocket):
    await websocket.accept()
    f = open("app.log")
    try:
        while True:
            lines = f.readlines()
            if not lines:
                await asyncio.sleep(1)
                continue
            for line in lines:
                await websocket.send_text(line)
    except WebSocketDisconnect:
        print("Disconnected client")
    finally:
        f.close()
