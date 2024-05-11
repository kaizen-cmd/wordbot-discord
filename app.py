import logging
import os

from WordChainClient import construct_client
from dotenv import load_dotenv

if ".env" not in os.listdir():
    raise Exception(".env not found")

load_dotenv(".env")

logging.basicConfig(
    filename="app.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger("app")


class App:

    TOKEN = ""
    CLIENT = construct_client()

    def __init__(self, token) -> None:
        App.TOKEN = token

    def run(self):
        App.CLIENT.run(App.TOKEN)


if __name__ == "__main__":
    app = App(os.getenv("BOT_TOKEN"))
    logger.info("Started Wordchain instance")
    app.run()
