#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: SDR Lab 02 - cabled FM transmitter (tone)
# Author: SDR Lab
# GNU Radio version: 3.10.12.0

from PyQt5 import Qt
from gnuradio import qtgui
from PyQt5 import QtCore
from gnuradio import analog
from gnuradio import blocks
from gnuradio import filter
from gnuradio.filter import firdes
from gnuradio import gr
from gnuradio.fft import window
import sys
import signal
from PyQt5 import Qt
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import eng_notation
from gnuradio import iio
import math
import sip
import threading



class lab02_fm_tx(gr.top_block, Qt.QWidget):

    def __init__(self):
        gr.top_block.__init__(self, "SDR Lab 02 - cabled FM transmitter (tone)", catch_exceptions=True)
        Qt.QWidget.__init__(self)
        self.setWindowTitle("SDR Lab 02 - cabled FM transmitter (tone)")
        qtgui.util.check_set_qss()
        try:
            self.setWindowIcon(Qt.QIcon.fromTheme('gnuradio-grc'))
        except BaseException as exc:
            print(f"Qt GUI: Could not set Icon: {str(exc)}", file=sys.stderr)
        self.top_scroll_layout = Qt.QVBoxLayout()
        self.setLayout(self.top_scroll_layout)
        self.top_scroll = Qt.QScrollArea()
        self.top_scroll.setFrameStyle(Qt.QFrame.NoFrame)
        self.top_scroll_layout.addWidget(self.top_scroll)
        self.top_scroll.setWidgetResizable(True)
        self.top_widget = Qt.QWidget()
        self.top_scroll.setWidget(self.top_widget)
        self.top_layout = Qt.QVBoxLayout(self.top_widget)
        self.top_grid_layout = Qt.QGridLayout()
        self.top_layout.addLayout(self.top_grid_layout)

        self.settings = Qt.QSettings("gnuradio/flowgraphs", "lab02_fm_tx")

        try:
            geometry = self.settings.value("geometry")
            if geometry:
                self.restoreGeometry(geometry)
        except BaseException as exc:
            print(f"Qt GUI: Could not restore geometry: {str(exc)}", file=sys.stderr)
        self.flowgraph_started = threading.Event()

        ##################################################
        # Variables
        ##################################################
        self.tx_atten = tx_atten = 70
        self.tx_amp = tx_amp = 0.5
        self.samp_rate = samp_rate = 2.4e6
        self.quad_rate = quad_rate = 240e3
        self.f_tx = f_tx = 434e6
        self.f_off = f_off = 250e3
        self.f_m = f_m = 1e3
        self.dev = dev = 5e3
        self.a_m = a_m = 1.0

        ##################################################
        # Blocks
        ##################################################

        self._tx_atten_range = qtgui.Range(10, 120, 1, 70, 200)
        self._tx_atten_win = qtgui.RangeWidget(self._tx_atten_range, self.set_tx_atten, "TX attenuation (dB)", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._tx_atten_win)
        self._f_tx_range = qtgui.Range(325e6, 1766e6, 25e3, 434e6, 200)
        self._f_tx_win = qtgui.RangeWidget(self._f_tx_range, self.set_f_tx, "Carrier frequency f_tx (Hz)", "counter", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._f_tx_win)
        self._f_m_range = qtgui.Range(100, 15e3, 1, 1e3, 200)
        self._f_m_win = qtgui.RangeWidget(self._f_m_range, self.set_f_m, "Tone f_m (Hz)", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._f_m_win)
        self._dev_range = qtgui.Range(500, 75e3, 50, 5e3, 200)
        self._dev_win = qtgui.RangeWidget(self._dev_range, self.set_dev, "Deviation (Hz)", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._dev_win)
        self._a_m_range = qtgui.Range(0, 1, 0.01, 1.0, 200)
        self._a_m_win = qtgui.RangeWidget(self._a_m_range, self.set_a_m, "Tone amplitude", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._a_m_win)
        self.tx_spec = qtgui.freq_sink_c(
            4096, #size
            window.WIN_BLACKMAN_hARRIS, #wintype
            0, #fc
            quad_rate, #bw
            "Transmitted FM signal (baseband)", #name
            1,
            None # parent
        )
        self.tx_spec.set_update_time(0.10)
        self.tx_spec.set_y_axis((-120), 0)
        self.tx_spec.set_y_label('Relative Gain', 'dB')
        self.tx_spec.set_trigger_mode(qtgui.TRIG_MODE_FREE, 0.0, 0, "")
        self.tx_spec.enable_autoscale(False)
        self.tx_spec.enable_grid(True)
        self.tx_spec.set_fft_average(0.1)
        self.tx_spec.enable_axis_labels(True)
        self.tx_spec.enable_control_panel(True)
        self.tx_spec.set_fft_window_normalized(False)



        labels = ['', '', '', '', '',
            '', '', '', '', '']
        widths = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        colors = ["blue", "red", "green", "black", "cyan",
            "magenta", "yellow", "dark red", "dark green", "dark blue"]
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0, 1.0]

        for i in range(1):
            if len(labels[i]) == 0:
                self.tx_spec.set_line_label(i, "Data {0}".format(i))
            else:
                self.tx_spec.set_line_label(i, labels[i])
            self.tx_spec.set_line_width(i, widths[i])
            self.tx_spec.set_line_color(i, colors[i])
            self.tx_spec.set_line_alpha(i, alphas[i])

        self._tx_spec_win = sip.wrapinstance(self.tx_spec.qwidget(), Qt.QWidget)
        self.top_layout.addWidget(self._tx_spec_win)
        self._tx_amp_range = qtgui.Range(0, 0.8, 0.01, 0.5, 200)
        self._tx_amp_win = qtgui.RangeWidget(self._tx_amp_range, self.set_tx_amp, "Digital amplitude", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._tx_amp_win)
        self.tone = analog.sig_source_f(quad_rate, analog.GR_COS_WAVE, f_m, a_m, 0, 0)
        self.to_dev_rate = filter.rational_resampler_ccc(
                interpolation=10,
                decimation=1,
                taps=[],
                fractional_bw=0)
        self.pluto = iio.fmcomms2_sink_fc32('192.168.1.10' if '192.168.1.10' else iio.get_pluto_uri(), [True, True], 32768, False)
        self.pluto.set_len_tag_key('')
        self.pluto.set_bandwidth(2000000)
        self.pluto.set_frequency((int(f_tx - f_off)))
        self.pluto.set_samplerate(int(samp_rate))
        self.pluto.set_attenuation(0, tx_atten)
        self.pluto.set_filter_params('Auto', '', 0, 0)
        self.offset = blocks.rotator_cc((2*math.pi*f_off/samp_rate), False)
        self.fm_mod = analog.frequency_modulator_fc((2*math.pi*dev/quad_rate))
        self.amp = blocks.multiply_const_cc(tx_amp)


        ##################################################
        # Connections
        ##################################################
        self.connect((self.amp, 0), (self.pluto, 0))
        self.connect((self.fm_mod, 0), (self.to_dev_rate, 0))
        self.connect((self.fm_mod, 0), (self.tx_spec, 0))
        self.connect((self.offset, 0), (self.amp, 0))
        self.connect((self.to_dev_rate, 0), (self.offset, 0))
        self.connect((self.tone, 0), (self.fm_mod, 0))


    def closeEvent(self, event):
        self.settings = Qt.QSettings("gnuradio/flowgraphs", "lab02_fm_tx")
        self.settings.setValue("geometry", self.saveGeometry())
        self.stop()
        self.wait()

        event.accept()

    def get_tx_atten(self):
        return self.tx_atten

    def set_tx_atten(self, tx_atten):
        self.tx_atten = tx_atten
        self.pluto.set_attenuation(0,self.tx_atten)

    def get_tx_amp(self):
        return self.tx_amp

    def set_tx_amp(self, tx_amp):
        self.tx_amp = tx_amp
        self.amp.set_k(self.tx_amp)

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.offset.set_phase_inc((2*math.pi*self.f_off/self.samp_rate))
        self.pluto.set_samplerate(int(self.samp_rate))

    def get_quad_rate(self):
        return self.quad_rate

    def set_quad_rate(self, quad_rate):
        self.quad_rate = quad_rate
        self.fm_mod.set_sensitivity((2*math.pi*self.dev/self.quad_rate))
        self.tone.set_sampling_freq(self.quad_rate)
        self.tx_spec.set_frequency_range(0, self.quad_rate)

    def get_f_tx(self):
        return self.f_tx

    def set_f_tx(self, f_tx):
        self.f_tx = f_tx
        self.pluto.set_frequency((int(self.f_tx - self.f_off)))

    def get_f_off(self):
        return self.f_off

    def set_f_off(self, f_off):
        self.f_off = f_off
        self.offset.set_phase_inc((2*math.pi*self.f_off/self.samp_rate))
        self.pluto.set_frequency((int(self.f_tx - self.f_off)))

    def get_f_m(self):
        return self.f_m

    def set_f_m(self, f_m):
        self.f_m = f_m
        self.tone.set_frequency(self.f_m)

    def get_dev(self):
        return self.dev

    def set_dev(self, dev):
        self.dev = dev
        self.fm_mod.set_sensitivity((2*math.pi*self.dev/self.quad_rate))

    def get_a_m(self):
        return self.a_m

    def set_a_m(self, a_m):
        self.a_m = a_m
        self.tone.set_amplitude(self.a_m)




def main(top_block_cls=lab02_fm_tx, options=None):

    qapp = Qt.QApplication(sys.argv)

    tb = top_block_cls()

    tb.start()
    tb.flowgraph_started.set()

    tb.show()

    def sig_handler(sig=None, frame=None):
        tb.stop()
        tb.wait()

        Qt.QApplication.quit()

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    timer = Qt.QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)

    qapp.exec_()

if __name__ == '__main__':
    main()
