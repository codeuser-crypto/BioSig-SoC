"""
data_logger.py - Append received samples to a timestamped CSV.

Columns: iso_timestamp, seq, sample_q15, voltage_mv
"""

from __future__ import annotations

import csv
import os
import time
from datetime import datetime, timezone


class DataLogger:
    def __init__(self, path: str | None = None, directory: str = "captures"):
        if path is None:
            os.makedirs(directory, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(directory, f"ecg_{stamp}.csv")
        self.path = path
        new_file = not os.path.exists(path)
        self._f = open(path, "a", newline="", encoding="utf-8")
        self._w = csv.writer(self._f)
        if new_file:
            self._w.writerow(["iso_timestamp", "seq", "sample_q15", "voltage_mv"])
        self.count = 0
        self._t0 = time.time()

    def log(self, seq: int, sample_q15: int, voltage_mv: float):
        ts = datetime.now(timezone.utc).isoformat()
        self._w.writerow([ts, seq, sample_q15, f"{voltage_mv:.5f}"])
        self.count += 1
        if self.count % 500 == 0:
            self._f.flush()

    def close(self):
        self._f.flush()
        self._f.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
