import os
import discord
from dotenv import load_dotenv
from MultiServerWordChainDB import MultiServerWordChainDB
from WordChainClient import WordChainClient
from app import App
from logging_config import get_logger
import multiprocessing

logger = get_logger(__name__)

if ".env" not in os.listdir():
    raise Exception(".env not found")

load_dotenv(".env")


def _constrcut_client(db):
    intents = discord.Intents.default()
    intents.messages = True
    intents.message_content = True
    return WordChainClient(db=db, intents=intents, command_prefix="/")


db = MultiServerWordChainDB()
client = _constrcut_client(db)
app = App(os.getenv("BOT_TOKEN"), client=client)


if __name__ == "__main__":
    from insights import run

    multiprocessing.Process(target=run).start()
    logger.info("Started Wordchain instance")
    app.run()
