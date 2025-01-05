import logging

logging.basicConfig(
    filename="logs/app.log",
    level=logging.ERROR,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


def get_logger(name):
    return logging.getLogger(name)
