import logging
import os
import sqlite3
from collections import namedtuple
from contextlib import asynccontextmanager

from fastapi import FastAPI, Form
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request

from elements import GamingRefreeEmbed
from scripts.get_bot_guilds import get_bot_guilds
from scripts.send_custom_message import send_embed_to_server, send_to_server
from scripts.send_dm import create_dm_channel, send_dm
from tasks import TaskQueue

logging.basicConfig(
    filename="logs/web.log",
    level=logging.DEBUG,
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


@app.post("/vote-callback")
async def vote_callback(request: Request):
    logger.info("Received vote callback")
    word_count = 5

    # Check for correct authorization
    if request.headers.get("Authorization") != "super_secret_password":
        logger.warning("Unauthorized vote callback attempt")
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
    logger.info("Home page accessed")
    guilds_meta = get_bot_guilds(servers=50)
    return templates.TemplateResponse(
        "home.html", {"request": request, "guilds_meta": guilds_meta}
    )


@app.get("/admin")
async def admin_get(request: Request):
    logger.info("Admin page accessed")
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

    inprogress_tasks = tq.get_inprogress()

    for server in servers:
        server["active_members"] = server_active_users_map.get(
            str(server["id"]), "DataNA"
        )

    return templates.TemplateResponse(
        "admin.html",
        {
            "request": request,
            "servers": servers,
            "active_members": active_members,
            "inprogress_tasks": inprogress_tasks,
        },
    )


@app.post("/admin")
async def admin_post(
    request: Request, username: str = Form(...), password: str = Form(...)
):
    logger.info("Admin login attempt")
    if username == "slav" and password == "Konnichiwa@11Hajimimashte@11":
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
