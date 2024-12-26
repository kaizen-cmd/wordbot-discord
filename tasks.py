from multiprocessing import Process, Queue, Lock, Manager
from scripts.send_custom_message import broadcast_embed, broadcast
import time


class TaskQueue:
    def __init__(self):
        self.queue = Queue(maxsize=3)
        self.lock = Lock()
        self.in_progress_buffer = Manager().list()
        self.timeout = 5  # timeout for get
        self.sleep_duration = 10

    def submit(self, target, data):
        self.queue.put({"target": target, "data": data})

    def process_item(self, item):
        if item["target"] == "broadcast_embed":
            broadcast_embed(item["data"])
        elif item["target"] == "broadcast":
            broadcast(item["data"])

    def _start_consumer(self):
        while True:
            try:
                item = self.queue.get(timeout=self.timeout)
                with self.lock:
                    self.in_progress_buffer.append(item)
                    print("ip buffer", len(self.in_progress_buffer))
                try:
                    self.process_item(item)
                finally:
                    with self.lock:
                        self.in_progress_buffer.remove(item)
            except Exception as e:
                print(f"Error: {e}")
            time.sleep(self.sleep_duration)

    def start_processing(self):
        self.consumer = Process(target=self._start_consumer, daemon=True)
        self.consumer.start()

    def stop(self):
        self.consumer.terminate()

    def get_inprogress(self):
        with self.lock:
            print("ip buffer in get", len(self.in_progress_buffer))
            return self.in_progress_buffer
