import itertools
import sys
import threading
import time
from collections import defaultdict
from typing import Union

import tqdm
from lib.core import CONFIG
from superannotate.logger import get_default_logger


class Spinner:
    spinner_cycle = iter(itertools.cycle(["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"]))

    def __init__(self):
        self.stop_running = threading.Event()
        self.spin_thread = threading.Thread(target=self.init_spin)

    def __enter__(self):
        self.spin_thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def start(self):
        self.spin_thread.start()

    def stop(self):
        self.stop_running.set()
        self.spin_thread.join()

    def init_spin(self):
        while not self.stop_running.is_set():
            sys.stdout.write(next(self.spinner_cycle))
            sys.stdout.flush()
            time.sleep(0.25)
            sys.stdout.write("\b")


class Reporter:
    def __init__(
        self,
        log_info: bool = True,
        log_warning: bool = True,
        disable_progress_bar: bool = False,
        log_debug: bool = True,
    ):
        self.logger = get_default_logger()
        self._log_info = log_info
        self._log_warning = log_warning
        self._log_debug = log_debug
        self._disable_progress_bar = disable_progress_bar
        self.info_messages = []
        self.warning_messages = []
        self.debug_messages = []
        self.custom_messages = defaultdict(set)
        self.progress_bar = None
        self.session = CONFIG.get_current_session()
        self._spinner = None

    @property
    def spinner(self):
        return Spinner()

    def start_spinner(self):
        if self._log_info:
            self._spinner = Spinner()
            self._spinner.start()

    def stop_spinner(self):
        if self._spinner:
            self._spinner.stop()

    def disable_info(self):
        self._log_info = False

    def enable_info(self):
        self._log_info = True

    def log_info(self, value: str):
        if self._log_info:
            self.logger.info(value)
        self.info_messages.append(value)

    def log_warning(self, value: str):
        if self._log_warning:
            self.logger.warning(value)
        self.warning_messages.append(value)

    def log_error(self, value: str):
        self.logger.error(value)

    def log_debug(self, value: str):
        if self._log_debug:
            self.logger.debug(value)
        self.debug_messages.append(value)

    def start_progress(
        self,
        iterations: Union[int, range],
        description: str = "Processing",
        disable=False,
    ):
        self.progress_bar = self.get_progress_bar(iterations, description, disable)

    @staticmethod
    def get_progress_bar(
        iterations: Union[int, range], description: str = "Processing", disable=False
    ):
        if isinstance(iterations, range):
            return tqdm.tqdm(iterations, desc=description, disable=disable)
        else:
            return tqdm.tqdm(total=iterations, desc=description, disable=disable)

    def finish_progress(self):
        self.progress_bar.close()

    def update_progress(self, value: int = 1):
        if self.progress_bar:
            self.progress_bar.update(value)

    def store_message(self, key: str, value: str):
        self.custom_messages[key].add(value)

    def track(self, key, value):
        if self.session:
            self.session[key] = value


class Progress:
    def __init__(self, iterations: Union[int, range], description: str = "Processing"):
        self._iterations = iterations
        self._description = description
        self._progress_bar = None

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        if self._progress_bar:
            self._progress_bar.close()

    def update(self, value=1):
        if not self._progress_bar:
            self._progress_bar = Reporter.get_progress_bar(
                self._iterations, self._description
            )
        self._progress_bar.update(value)
