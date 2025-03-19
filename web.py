import asyncio
import logging
import os
import json
import sqlite3
import datetime
from collections import namedtuple
from contextlib import asynccontextmanager

from fastapi import Response
from fastapi import FastAPI, Form, WebSocketDisconnect
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.websockets import WebSocket
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request

from elements import GamingRefreeEmbed
from scripts.get_bot_guilds import get_bot_guilds
from scripts.send_custom_message import send_embed_to_server, send_to_server
from scripts.send_dm import create_dm_channel, send_dm
from tasks import TaskQueue

logging.basicConfig(
    filename="logs/web.log",
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

tq = TaskQueue()


@asynccontextmanager
async def lifespan(app: FastAPI):
    tq.start_processing()
    yield
    tq.stop()


app = FastAPI(lifespan=lifespan)


# Add session middleware for managing sessions
app.add_middleware(SessionMiddleware, secret_key="1qaz2wsx3edc4rfv")

# Set up templates
templates = Jinja2Templates(directory="templates")

# mount static files
app.mount("/static/", StaticFiles(directory="static"), name="static")


def validate_top_gg_webhook(data, headers):
    # Check for correct authorization
    if headers.get("Authorization") != "super_secret_password":
        logger.warning("Unauthorized vote callback attempt")
        raise Exception("Unauthorized")

    type_ = data["type"]
    bot = data["bot"]

    if bot != os.getenv("BOT_ID") or type_ != "upvote":
        raise Exception("Invalid request")


def validate_discordbotlist_webhook(data, headers):
    # Check for correct authorization
    if headers.get("origin") != "https://discordbotlist.com":
        raise Exception("Unauthorized")


@app.post("/vote-callback")
async def vote_callback(request: Request):
    logger.info("Received vote callback")
    word_count = 5

    data = await request.json()
    headers = request.headers

    is_valid = False
    try:
        validate_discordbotlist_webhook(data, headers)
        is_valid = True
    except Exception as e:
        logger.warning("Not a discordbotlist call", e)

    try:
        validate_top_gg_webhook(data, headers)
        is_valid = True
    except Exception as e:
        logger.warning("Not a top.gg call", e)

    if not is_valid:
        return "Invalid request"

    user_id = int(data.get("user") or data.get("id"))

    if not user_id:
        logger.warning("Received a vote callback without user id")
        return "Invalid request"

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
    logger.info("Home page accessed")
    guilds_meta = get_bot_guilds(servers=50)
    return templates.TemplateResponse(
        "home.html", {"request": request, "guilds_meta": guilds_meta}
    )


@app.get("/refund")
async def home(request: Request):
    return templates.TemplateResponse("refund.html", {"request": request})


@app.get("/privacy")
async def home(request: Request):
    return templates.TemplateResponse("privacy.html", {"request": request})


@app.get("/tos")
async def home(request: Request):
    return templates.TemplateResponse("tandc.html", {"request": request})


@app.post("/payments")
async def home(request: Request):
    body = await request.body()
    data = json.loads(body.decode("utf-8"))
    event = data["type"]
    if not event in ("subscription.active", "subscription.renewed"):
        return Response(status_code=200)
    expiry_date = data["data"]["next_billing_date"]
    discord_user_id = data["data"]["metadata"]["discordUserId"]
    db = sqlite3.connect("db.sqlite3")
    curr = db.cursor()
    dt = datetime.datetime.strptime(expiry_date, "%Y-%m-%dT%H:%M:%S.%fZ").replace(
        tzinfo=datetime.timezone.utc
    )
    sqlite_timestamp = dt.strftime("%Y-%m-%d %H:%M:%S.%f")
    curr.execute(
        "INSERT INTO subscription(user_id, subscription_end_date) VALUES (?, ?)",
        (
            discord_user_id,
            sqlite_timestamp,
        ),
    )
    db.commit()
    curr.close()
    db.close()
    channel_id = create_dm_channel(discord_user_id)
    send_dm(
        channel_id,
        f"Thanks for subscribing to premium, your subscription will expire on {expiry_date}",
    )
    channel_id = create_dm_channel(os.getenv("SLAV_USER_ID"))
    send_dm(
        channel_id,
        f"Someone Subscribed!",
    )
    return Response(status_code=200)


@app.get("/admin")
async def admin_get(request: Request):
    if not request.session.get("authenticated"):
        return templates.TemplateResponse("login.html", {"request": request})

    inprogress_tasks = tq.get_inprogress()

    return templates.TemplateResponse(
        "admin.html",
        {
            "request": request,
            "inprogress_tasks": inprogress_tasks,
        },
    )


@app.websocket("/ws")
async def websocket_logs_endpoint(websocket: WebSocket):
    logger.info("Websocket connection established")
    await websocket.accept()
    if websocket.session.get("authenticated", False) != True:
        await websocket.close()
        return
    with open("logs/web.log", "r") as f:
        f.readlines()
        try:
            while True:
                line = f.readline()
                if not line:
                    await asyncio.sleep(1)
                    continue
                await websocket.send_text(line)
        except WebSocketDisconnect:
            websocket.close()


@app.get("/servers")
def get_servers(request: Request):
    if not request.session.get("authenticated"):
        return templates.TemplateResponse("login.html", {"request": request})

    servers = get_bot_guilds()
    active_members = 0
    server_active_users_map = dict()

    conn = sqlite3.connect("db.sqlite3")
    curr = conn.cursor()
    curr.execute("SELECT COUNT(server_id), server_id FROM users GROUP BY server_id")
    server_member_count = curr.fetchall()

    for member_count, server_id in server_member_count:
        server_active_users_map[server_id] = member_count
        active_members += member_count

    curr.close()
    conn.close()

    for server in servers:
        server["active_members"] = server_active_users_map.get(
            str(server["id"]), "DataNA"
        )

    return {
        "servers": servers,
        "active_members": active_members,
    }


@app.post("/admin")
async def admin_post(
    request: Request, username: str = Form(...), password: str = Form(...)
):
    logger.info("Admin login attempt")
    conn = sqlite3.connect("db.sqlite3")
    curr = conn.cursor()
    curr.execute("SELECT * FROM admin_creds LIMIT 1")
    admin_creds = curr.fetchone()
    curr.close()
    conn.close()
    username_, password_ = admin_creds
    if username == username_ and password == password_:
        request.session["authenticated"] = True
    return RedirectResponse("/admin", status_code=303)


@app.post("/send_message")
async def send_message(
    request: Request, message: str = Form(...), server_id: str = Form(...)
):
    logger.info(f"Sending message to server {server_id}")
    if request.session.get("authenticated") != True:
        return RedirectResponse("/admin", status_code=303)
    send_to_server(message, server_id)
    return RedirectResponse("/admin", status_code=303)


@app.post("/broadcast")
async def broadcast_message(request: Request, broadcast_message: str = Form(...)):
    logger.info("Broadcasting message")
    if request.session.get("authenticated") != True:
        return RedirectResponse("/admin", status_code=303)
    tq.submit(target="broadcast", data=broadcast_message)
    return RedirectResponse("/admin", status_code=303)


@app.post("/broadcast-embed")
async def broadcast_embed_(
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    image: str = Form(None),
):
    logger.info("Broadcasting embed")
    if request.session.get("authenticated") != True:
        return RedirectResponse("/admin", status_code=303)
    embed = GamingRefreeEmbed(
        title=title,
        description=description,
        image_url=image if image else None,
    )
    tq.submit(target="broadcast_embed", data=embed.to_dict())
    return RedirectResponse("/admin", status_code=303)


@app.post("/unicast-embed")
async def unicast_embed(
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    server_id: str = Form(...),
    image: str = Form(None),
):
    logger.info(f"Unicasting embed to server {server_id}")
    if request.session.get("authenticated") != True:
        return RedirectResponse("/admin", status_code=303)

    embed = GamingRefreeEmbed(
        title=title,
        description=description,
        image_url=image if image else None,
    )

    send_embed_to_server(embed.to_dict(), server_id)
    return RedirectResponse("/admin", status_code=303)
