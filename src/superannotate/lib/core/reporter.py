import logging
from collections import defaultdict
from typing import Union

import tqdm


class Reporter:
    def __init__(
        self,
        log_info: bool = True,
        log_warning: bool = True,
        disable_progress_bar: bool = False,
        log_debug: bool = True,
    ):
        self.logger = logging.getLogger("root")
        self._log_info = log_info
        self._log_warning = log_warning
        self._log_debug = log_debug
        self._disable_progress_bar = disable_progress_bar
        self.info_messages = []
        self.warning_messages = []
        self.debug_messages = []
        self.custom_messages = defaultdict(set)
        self.progress_bar = None

    def log_info(self, value: str):
        if self._log_info:
            self.logger.info(value)
        self.info_messages.append(value)

    def log_warning(self, value: str):
        if self._log_warning:
            self.logger.warning(value)
        self.warning_messages.append(value)

    def log_debug(self, value: str):
        if self._log_debug:
            self.logger.debug(value)
        self.debug_messages.append(value)

    def start_progress(
        self, iterations: Union[int, range], description: str = "Processing"
    ):
        if isinstance(iterations, range):
            self.progress_bar = tqdm.tqdm(
                iterations, desc=description, disable=self._disable_progress_bar
            )
        else:
            self.progress_bar = tqdm.tqdm(
                total=iterations, desc=description, disable=self._disable_progress_bar
            )

    def finish_progress(self):
        self.progress_bar.close()

    def update_progress(self, value: int = 1):
        self.progress_bar.update(value)

    def generate_report(self) -> str:
        report = ""
        if self.info_messages:
            report += "\n".join(self.info_messages)
        if self.warning_messages:
            report += "\n".join(self.warning_messages)
        return report

    def store_message(self, key: str, value: str):
        self.custom_messages[key].add(value)

    @property
    def messages(self):
        for key, values in self.custom_messages.items():
            yield f"{key} [{', '.join(values)}]"
