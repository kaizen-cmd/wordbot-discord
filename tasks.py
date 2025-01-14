import time
from multiprocessing import Lock, Manager, Process, Queue

from scripts.send_custom_message import broadcast, broadcast_embed
import logging

logging.basicConfig(
    filename="logs/web.log",
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("task_queue")


class TaskQueue:
    def __init__(self):
        logger.info("TaskQueue init")
        self.queue = Queue(maxsize=3)
        self.lock = Lock()
        self.in_progress_buffer = Manager().list()
        self.timeout = 5  # timeout for get
        self.sleep_duration = 2

    def submit(self, target, data):
        self.queue.put({"target": target, "data": data})

    def process_item(self, item):
        logger.info(f"Processing item {item["target"]}")
        with self.lock:
            self.in_progress_buffer.append(item)
        if item["target"] == "broadcast_embed":
            broadcast_embed(item["data"])
        elif item["target"] == "broadcast":
            broadcast(item["data"])
        with self.lock:
            self.in_progress_buffer.remove(item)

    def _start_consumer(self):
        while True:
            try:
                item = self.queue.get(timeout=self.timeout)
                self.process_item(item)
            except Exception as e:
                pass
            time.sleep(self.sleep_duration)

    def start_processing(self):
        self.consumer = Process(target=self._start_consumer, daemon=True)
        self.consumer.start()

    def stop(self):
        self.consumer.terminate()

    def get_inprogress(self):
        with self.lock:
            return self.in_progress_buffer
