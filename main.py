import os

import discord
from dotenv import load_dotenv

from app import App
from insights import Insights
from logging_config import get_logger
from MultiServerWordChainDB import MultiServerWordChainDB
from WordChainClient import WordChainClient

logger = get_logger(__name__)

if ".env" not in os.listdir():
    raise Exception(".env not found")

load_dotenv(".env")

def _constrcut_client(db, insights):

    intents = discord.Intents.default()
    intents.messages = True
    intents.message_content = True
    return WordChainClient(
        db=db, insights=insights, intents=intents, command_prefix="/"
    )

db = MultiServerWordChainDB()
insights = Insights(db)
client = _constrcut_client(db, insights)
app = App(os.getenv("BOT_TOKEN"), client=client)

if __name__ == "__main__":
    logger.info("Started Wordchain instance")
    app.run()
