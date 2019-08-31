import time
import threading


class Timer(threading.Thread):
    def __init__(self):
        super().__init__()
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def is_stopped(self):
        return self._stop_event.is_set()

    def run(self):
        start_time = time.time()
        while not self.is_stopped():
            elapsed_time = time.time() - start_time
            print(f"\rProcessing (elapsed time {elapsed_time:.3f} s)...", end="")
            time.sleep(0.01)
        print(' Finished')
        print()
