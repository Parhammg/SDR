"""Hardware-free checks for the Lab 01 recorder using GNU Radio 3.10."""

from pathlib import Path
import unittest
from uuid import uuid4

import numpy as np
from gnuradio import analog, blocks, gr

from sdrlab_iq_recorder import blk


class RecorderChecks(unittest.TestCase):
    def setUp(self):
        self.folder = Path(__file__).resolve().parent / f'_recorder_check_{uuid4().hex}'
        self.addCleanup(self.cleanup_recordings)
        self.recorder = blk(team="Team-01", fc=434000000, fs=2600000,
                            gain=10, max_seconds=0.0100002, folder=str(self.folder))
        self.addCleanup(self.recorder.stop)
        self.input = np.ones(32768, dtype=np.complex64)

    def files(self):
        return list(self.folder.glob("*.cf32"))

    def cleanup_recordings(self):
        if self.folder.exists():
            for path in self.files():
                path.unlink()
            self.folder.rmdir()

    def feed(self, count):
        self.assertEqual(self.recorder.work([self.input[:count]], []), count)

    def test_cap_consumes_remaining_samples_and_requires_rearming(self):
        self.feed(16)
        self.assertEqual(self.files(), [])
        self.recorder.record = True
        self.feed(8192)
        self.feed(32768)
        self.feed(4096)
        recorded, = self.files()
        self.assertRegex(recorded.name, r"^Team-01_lab01_434000000_2600000_10\.0_\d{8}T\d{6}\.cf32$")
        self.assertEqual(recorded.stat().st_size, 8 * 26000)
        self.recorder.record = False
        self.recorder.record = True
        self.feed(500)
        self.recorder.record = False
        self.assertEqual(sorted(p.stat().st_size for p in self.files()), [4000, 208000])

    def test_setting_changes_close_and_wait(self):
        for index, (parameter, value) in enumerate((('fc', 434100000), ('fs', 5000000), ('gain', 8)), 1):
            self.recorder.record = True
            self.feed(1024)
            setattr(self.recorder, parameter, value)
            self.feed(512)
            self.assertEqual(len(self.files()), index)
            self.assertTrue(all(p.stat().st_size == 8192 for p in self.files()))
            self.recorder.record = False

    def test_gnuradio_tone_and_flowgraph_stop(self):
        self.recorder.record = True
        graph = gr.top_block()
        graph.connect(analog.sig_source_c(2600000, analog.GR_COS_WAVE, 100000, 0.5),
                      blocks.throttle(gr.sizeof_gr_complex, 2600000),
                      blocks.head(gr.sizeof_gr_complex, 8320), self.recorder)
        graph.run()
        recorded, = self.files()
        iq = np.fromfile(recorded, dtype='<c8')
        self.assertEqual(len(iq), 8320)
        freq = np.fft.fftfreq(len(iq), 1 / 2600000)
        self.assertAlmostEqual(freq[np.argmax(abs(np.fft.fft(iq)))], 100000)


if __name__ == '__main__':
    unittest.main()
