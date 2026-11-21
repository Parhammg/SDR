"""
SDR Lab I/Q recorder -- source code for a GNU Radio Companion "Python Block".

Writes raw complex-float32 (cf32) I/Q files named by the lab rule
    teamID_labNN_fc_fs_gain_timestamp.cf32
e.g. Team-07_lab01_98000000_2048000_40.2_20261005T101502.cf32

* A new file is opened each time `record` changes from False to True.
* Recording stops when `record` returns to False or after `max_seconds`.
* If fc, fs or gain change while recording, the file is closed, so one
  file never mixes two settings (untick / tick `record` for a new take).
"""
import os
import time

import numpy as np
from gnuradio import gr


class blk(gr.sync_block):
    def __init__(self, team='Team-00', lab=1, fc=100e6, fs=2.048e6, gain=0.0,
                 record=False, max_seconds=5.0, folder='.'):
        gr.sync_block.__init__(self, name='SDR Lab IQ Recorder',
                               in_sig=[np.complex64], out_sig=None)
        # Attributes named like the arguments can be changed at run time
        # from GRC variables (QT GUI Range, QT GUI Check Box, ...).
        self.team, self.lab = team, lab
        self.fc, self.fs, self.gain = fc, fs, gain
        self.record, self.max_seconds, self.folder = record, max_seconds, folder
        self._fh = None       # open file (None = not recording)
        self._n = 0           # samples written to the current file
        self._key = None      # (fc, fs, gain) when the file was opened
        self._armed = True    # False after a take until `record` is released

    def _open(self):
        stamp = time.strftime('%Y%m%dT%H%M%S')
        name = '%s_lab%02d_%d_%d_%.1f_%s.cf32' % (
            self.team, int(self.lab), round(self.fc), round(self.fs),
            self.gain, stamp)
        os.makedirs(self.folder, exist_ok=True)
        self._fh = open(os.path.join(self.folder, name), 'wb')
        self._n, self._key = 0, (self.fc, self.fs, self.gain)
        print('[REC] start ' + name)

    def _close(self, why):
        self._fh.close()
        self._fh, self._armed = None, False
        print('[REC] stop  %d samples = %.2f s (%s)'
              % (self._n, self._n / self.fs, why))

    def work(self, input_items, output_items):
        x = input_items[0]
        if not self.record:
            if self._fh is not None:
                self._close('record off')
            self._armed = True
        elif self._fh is None and self._armed:
            self._open()
        if self._fh is not None:
            if (self.fc, self.fs, self.gain) != self._key:
                self._close('fc/fs/gain changed')
            else:
                left = int(self.max_seconds * self.fs) - self._n
                n = min(len(x), left)
                x[:n].tofile(self._fh)
                self._n += n
                if n == left:
                    self._close('max_seconds reached')
        return len(x)

    def stop(self):
        if self._fh is not None:
            self._close('flowgraph stopped')
        return True
