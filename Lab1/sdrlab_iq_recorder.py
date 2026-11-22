"""Embedded GNU Radio sink for headerless, little-endian complex float32 I/Q."""

from datetime import datetime, timedelta
from math import floor
from pathlib import Path
from threading import Lock

import numpy as np
from gnuradio import gr


class blk(gr.sync_block):
    """Record one file per arming and stop at the configured sample limit."""

    def __init__(self, team='Team-00', lab=1, fc=100e6, fs=2.6e6, gain=0.0,
                 record=False, max_seconds=5.0, folder='.'):
        gr.sync_block.__init__(self, name='SDR Lab IQ Recorder',
                               in_sig=[np.complex64], out_sig=None)
        self.team = team
        self.lab = lab
        self.folder = folder
        self.max_seconds = max_seconds
        self._lock = Lock()
        self._fc = fc
        self._fs = fs
        self._gain = gain
        self._record = bool(record)
        self._file = None
        self._wait_for_uncheck = False

    @property
    def fc(self):
        return self._fc

    @fc.setter
    def fc(self, value):
        self._set_capture_setting('_fc', value, 'fc changed')

    @property
    def fs(self):
        return self._fs

    @fs.setter
    def fs(self, value):
        self._set_capture_setting('_fs', value, 'fs changed')

    @property
    def gain(self):
        return self._gain

    @gain.setter
    def gain(self, value):
        self._set_capture_setting('_gain', value, 'gain changed')

    def _set_capture_setting(self, attribute, value, reason):
        with self._lock:
            if value != getattr(self, attribute) and self._file is not None:
                self._close_file(reason)
                self._wait_for_uncheck = True
            setattr(self, attribute, value)

    @property
    def record(self):
        return self._record

    @record.setter
    def record(self, value):
        with self._lock:
            self._record = bool(value)
            if not self._record:
                self._close_file('record unchecked')
                self._wait_for_uncheck = False

    def _open_file(self):
        folder = Path(self.folder)
        folder.mkdir(parents=True, exist_ok=True)
        self._file_fs = round(self._fs)
        self._limit = floor(float(self.max_seconds) * self._file_fs)
        self._written = 0
        stamp = datetime.now()
        prefix = f'{self.team}_lab{int(self.lab):02d}_{round(self._fc)}_{self._file_fs}_{self._gain:.1f}'
        while True:
            path = folder / f'{prefix}_{stamp:%Y%m%dT%H%M%S}.cf32'
            try:
                self._file = path.open('xb')
                break
            except FileExistsError:
                # Keep the required filename format when rearmed within a second.
                stamp += timedelta(seconds=1)
        print(f'[REC] start {path.name}', flush=True)

    def _close_file(self, reason):
        if self._file is not None:
            self._file.close()
            self._file = None
            print(f'[REC] stop {self._written} samples = '
                  f'{self._written / self._file_fs:.2f} s ({reason})', flush=True)

    def work(self, input_items, output_items):
        samples = input_items[0]
        with self._lock:
            if self._record and not self._wait_for_uncheck and len(samples):
                if self._file is None:
                    self._open_file()
                count = min(len(samples), self._limit - self._written)
                samples[:count].astype('<c8', copy=False).tofile(self._file)
                self._written += count
                if self._written == self._limit:
                    self._close_file('max_seconds reached')
                    self._wait_for_uncheck = True
        return len(samples)

    def stop(self):
        with self._lock:
            self._close_file('flowgraph stopped')
        return True
