from WordChainClient import client
import logging
import os

logging.basicConfig(
    filename="app.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger("app")


class App:

    TOKEN = ""
    CLIENT = client

    def __init__(self, token) -> None:
        App.TOKEN = token

    def run(self):
        App.CLIENT.run(App.TOKEN)


if __name__ == "__main__":
    app = App(
        "MTIyNTQ5MDc1OTQzMjc5ODMyMA.GBK0hM.7cIV6gluTopYAOsmtbYD0hkvmgChVAeYTWJDdg"
    )
    logger.info("Started Wordchain instance")
    app.run()
