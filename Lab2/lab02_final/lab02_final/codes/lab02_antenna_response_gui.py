#!/usr/bin/env python3
"""PlutoSDR relative antenna-link response measurement (GNU Radio 3.10 / PyQt5).

Run in the GNU Radio Python environment:
    python -m pip install pyqtgraph
    python antenna_response_gui.py

This measures uncalibrated received tone power, NOT antenna gain or S11.
Use two antennas, or an appropriately attenuated conducted connection.
Never connect Pluto TX directly to RX without suitable attenuation.
"""
import os
import sys
import signal
import time
import threading

# Select the same Qt binding for GNU Radio and PyQtGraph.
# This must be set before importing pyqtgraph.
os.environ["PYQTGRAPH_QT_LIB"] = "PyQt5"
from PyQt5 import QtCore, QtWidgets
import numpy as np
import pyqtgraph as pg
from gnuradio import analog, blocks, filter, gr, iio
from gnuradio.filter import firdes


URI = "ip:192.168.1.10"
SAMPLE_RATE = 1_000_000
TONE_HZ = 100_000
SETTLE_SECONDS = 2.0  # Starting value; verify against hardware/buffering.
MEASUREMENT_SECONDS = 0.5


class PowerCollector(gr.sync_block):
    """Collect fresh power samples after a GUI-controlled settling interval."""

    def __init__(self):
        gr.sync_block.__init__(self, name="Power collector",
                               in_sig=[np.float32], out_sig=None)
        self.guard = threading.Lock()
        self.accept_after = float("inf")
        self.total = 0.0
        self.count = 0

    def reset(self, accept_after):
        with self.guard:
            self.accept_after = accept_after
            self.total = 0.0
            self.count = 0

    def snapshot(self):
        with self.guard:
            return self.total, self.count

    def work(self, input_items, output_items):
        values = input_items[0]
        with self.guard:
            if time.monotonic() >= self.accept_after:
                self.total += float(np.sum(values, dtype=np.float64))
                self.count += len(values)
        return len(values)


class AntennaResponseGUI(gr.top_block, QtWidgets.QWidget):
    def __init__(self):
        gr.top_block.__init__(self, "Pluto antenna response", catch_exceptions=True)
        QtWidgets.QWidget.__init__(self)
        self.setWindowTitle("PlutoSDR — relative antenna-link response")
        self.resize(1100, 750)
        self.response_points = {}
        self.rf_hz = 400_000_000
        self.auto_running = False
        self.closed = False
        self.started = False

        layout = QtWidgets.QVBoxLayout(self)
        controls = QtWidgets.QGridLayout()
        layout.addLayout(controls)

        self.frequency = QtWidgets.QDoubleSpinBox()
        self.frequency.setRange(400.0, 3000.0)
        self.frequency.setDecimals(3)
        self.frequency.setSingleStep(10.0)
        self.frequency.setSuffix(" MHz")
        self.frequency.setValue(400.0)
        controls.addWidget(QtWidgets.QLabel("Actual test RF frequency"), 0, 0)
        controls.addWidget(self.frequency, 0, 1)

        self.tx_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.tx_slider.setRange(0, 359)
        self.tx_slider.setValue(200)  # 50 dB
        self.tx_label = QtWidgets.QLabel("TX1 attenuation: 50.00 dB")
        controls.addWidget(self.tx_label, 1, 0)
        controls.addWidget(self.tx_slider, 1, 1)

        self.rx_gain = QtWidgets.QSpinBox()
        self.rx_gain.setRange(0, 70)
        self.rx_gain.setValue(20)
        self.rx_gain.setSuffix(" dB")
        controls.addWidget(QtWidgets.QLabel("RX1 manual gain"), 2, 0)
        controls.addWidget(self.rx_gain, 2, 1)

        self.step = QtWidgets.QDoubleSpinBox()
        self.step.setRange(0.1, 2600.0)
        self.step.setValue(20.0)
        self.step.setSuffix(" MHz")
        controls.addWidget(QtWidgets.QLabel("Automatic sweep step"), 3, 0)
        controls.addWidget(self.step, 3, 1)

        buttons = QtWidgets.QHBoxLayout()
        layout.addLayout(buttons)
        self.start_button = QtWidgets.QPushButton("Start automatic sweep")
        self.stop_button = QtWidgets.QPushButton("Stop sweep")
        self.clear_button = QtWidgets.QPushButton("Clear plot")
        self.save_button = QtWidgets.QPushButton("Save CSV")
        for button in (self.start_button, self.stop_button,
                       self.clear_button, self.save_button):
            buttons.addWidget(button)

        self.plot = pg.PlotWidget(title="Received tone power — Max Hold per RF frequency")
        self.plot.setLabel("bottom", "Actual RF frequency", units="MHz")
        self.plot.setLabel("left", "Received tone power", units="dB relative")
        self.plot.showGrid(x=True, y=True)
        self.plot.setXRange(400, 3000, padding=0)
        self.curve = self.plot.plot(pen=pg.mkPen("y", width=2),
                                    symbol="o", symbolSize=4)
        layout.addWidget(self.plot)
        self.status = QtWidgets.QLabel("Starting…")
        layout.addWidget(self.status)
        note = QtWidgets.QLabel(
            "Uncalibrated link response, not antenna gain or S11. "
            "Keep geometry and gains fixed. Settling: 2 s; acquisition: 0.5 s."
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        lo_hz = self.rf_hz - TONE_HZ
        self.source = iio.fmcomms2_source_fc32(URI, [True, True], 32768)
        self.source.set_len_tag_key("packet_len")
        self.source.set_frequency(lo_hz)
        self.source.set_samplerate(SAMPLE_RATE)
        self.source.set_gain_mode(0, "manual")
        self.source.set_gain(0, 20)
        self.source.set_quadrature(True)
        self.source.set_rfdc(True)
        self.source.set_bbdc(True)
        self.source.set_filter_params("Auto", "", 0, 0)

        self.sink = iio.fmcomms2_sink_fc32(URI, [True, True], 32768, False)
        self.sink.set_len_tag_key("")
        self.sink.set_samplerate(SAMPLE_RATE)
        self.sink.set_frequency(lo_hz)
        self.sink.set_attenuation(0, 50.0)
        self.sink.set_filter_params("Auto", "", 0, 0)

        # Amplitude 0.5 leaves digital headroom.
        self.tone = analog.sig_source_c(SAMPLE_RATE, analog.GR_SIN_WAVE,
                                        TONE_HZ, 0.5, 0, 0)
        self.tone_filter = filter.freq_xlating_fir_filter_ccc(
            10, firdes.low_pass(1.0, SAMPLE_RATE, 5000, 5000),
            TONE_HZ, SAMPLE_RATE)
        self.mag_squared = blocks.complex_to_mag_squared(1)
        self.collector = PowerCollector()
        self.connect(self.tone, self.sink)
        self.connect(self.source, self.tone_filter,
                     self.mag_squared, self.collector)

        self.frequency.valueChanged.connect(self.change_frequency)
        self.tx_slider.valueChanged.connect(self.change_tx)
        self.rx_gain.valueChanged.connect(self.change_rx)
        self.start_button.clicked.connect(self.start_sweep)
        self.stop_button.clicked.connect(self.stop_sweep)
        self.clear_button.clicked.connect(self.clear_response)
        self.save_button.clicked.connect(self.save_csv)
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_response)
        self.timer.start(100)

    def arm_measurement(self):
        self.accept_after = time.monotonic() + SETTLE_SECONDS
        self.collector.reset(self.accept_after)
        self.status.setText(f"Settling at {self.rf_hz / 1e6:.3f} MHz…")

    def begin(self):
        self.start()
        self.started = True
        self.arm_measurement()

    def change_frequency(self, mhz):
        self.collector.reset(float("inf"))
        self.rf_hz = int(round(mhz * 1e6))
        lo_hz = self.rf_hz - TONE_HZ
        self.sink.set_frequency(lo_hz)
        self.source.set_frequency(lo_hz)
        self.arm_measurement()

    def change_tx(self, value):
        attenuation = value / 4.0
        self.sink.set_attenuation(0, attenuation)
        self.tx_label.setText(f"TX1 attenuation: {attenuation:.2f} dB")
        self.clear_response()

    def change_rx(self, value):
        self.source.set_gain(0, value)
        self.clear_response()

    def clear_response(self):
        self.response_points.clear()
        self.curve.setData([], [])
        self.arm_measurement()

    def record_response(self, rf_hz, power_db):
        if not np.isfinite(power_db):
            return
        self.response_points[rf_hz] = max(
            self.response_points.get(rf_hz, -np.inf), power_db)
        frequencies = sorted(self.response_points)
        self.curve.setData(np.asarray(frequencies) / 1e6,
                           [self.response_points[f] for f in frequencies])

    def update_response(self):
        if not self.started or time.monotonic() < self.accept_after:
            return
        total, count = self.collector.snapshot()
        # After decimation, the measurement rate is SAMPLE_RATE / 10.
        if count < int(MEASUREMENT_SECONDS * SAMPLE_RATE / 10):
            self.status.setText(f"Measuring at {self.rf_hz / 1e6:.3f} MHz…")
            return
        mean_power = total / count
        if not np.isfinite(mean_power) or mean_power <= 0:
            self.status.setText("No valid power measurement; check RX samples.")
            return
        power_db = 10.0 * np.log10(mean_power)
        # Plot updates are made here, in the Qt GUI thread.
        self.record_response(self.rf_hz, power_db)
        self.status.setText(
            f"RF: {self.rf_hz / 1e6:.3f} MHz | "
            f"Power: {power_db:.2f} dB relative | "
            f"Stored frequencies: {len(self.response_points)}")
        if self.auto_running:
            if self.rf_hz >= 3_000_000_000:
                self.stop_sweep()
                self.status.setText("Sweep complete — use Save CSV to export.")
            else:
                next_hz = min(3_000_000_000,
                              self.rf_hz + int(round(self.step.value() * 1e6)))
                self.frequency.setValue(next_hz / 1e6)
        else:
            # Independent acquisition windows for fixed-frequency Max Hold.
            self.accept_after = time.monotonic()
            self.collector.reset(self.accept_after)

    def start_sweep(self):
        self.auto_running = True
        for widget in (self.frequency, self.tx_slider, self.rx_gain,
                       self.step, self.start_button):
            widget.setEnabled(False)
        self.clear_response()
        self.frequency.setValue(400.0)
        self.arm_measurement()

    def stop_sweep(self):
        self.auto_running = False
        for widget in (self.frequency, self.tx_slider, self.rx_gain,
                       self.step, self.start_button):
            widget.setEnabled(True)

    def save_csv(self):
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save response", "antenna_response.csv", "CSV files (*.csv)")
        if filename:
            frequencies = sorted(self.response_points)
            data = np.asarray([[f, self.response_points[f]] for f in frequencies])
            data = data.reshape((-1, 2))
            np.savetxt(filename, data, delimiter=",",
                       header="rf_frequency_hz,max_received_power_db_relative",
                       comments="")
            self.status.setText(f"Saved: {filename}")

    def closeEvent(self, event):
        if not self.closed:
            self.closed = True
            self.timer.stop()
            if self.started:
                self.stop()
                self.wait()
        event.accept()


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = AntennaResponseGUI()
    window.show()
    window.begin()
    signal.signal(signal.SIGINT, lambda *_: window.close())
    signal.signal(signal.SIGTERM, lambda *_: window.close())
    heartbeat = QtCore.QTimer()
    heartbeat.timeout.connect(lambda: None)
    heartbeat.start(500)
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
