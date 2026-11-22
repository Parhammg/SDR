#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: SDR Lab 02 - FM receiver with two detectors
# Author: SDR Lab
# GNU Radio version: 3.10.12.0

from PyQt5 import Qt
from gnuradio import qtgui
from PyQt5 import QtCore
from PyQt5.QtCore import QObject, pyqtSlot
from gnuradio import analog
import math
from gnuradio import audio
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
import lab02_fm_rx_recorder as recorder  # embedded python block
import sip
import threading



class lab02_fm_rx(gr.top_block, Qt.QWidget):

    def __init__(self):
        gr.top_block.__init__(self, "SDR Lab 02 - FM receiver with two detectors", catch_exceptions=True)
        Qt.QWidget.__init__(self)
        self.setWindowTitle("SDR Lab 02 - FM receiver with two detectors")
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

        self.settings = Qt.QSettings("gnuradio/flowgraphs", "lab02_fm_rx")

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
        self.dev = dev = 75e3
        self.audio_bw = audio_bw = 15e3
        self.volume = volume = 0.3
        self.team = team = "Team-00"
        self.tau = tau = (50e-6)
        self.samp_rate = samp_rate = 2.4e6
        self.rf_gain = rf_gain = 20.7
        self.rec = rec = False
        self.quad_rate = quad_rate = 240e3
        self.ppm = ppm = 0
        self.pll_bw = pll_bw = 0.05
        self.fc = fc = 98.0e6
        self.f_off = f_off = 250e3
        self.f_m = f_m = 1e3
        self.f_fine = f_fine = 0
        self.det = det = 0
        self.chan_bw = chan_bw = min(2*(dev + audio_bw), 200e3)
        self.audio_rate = audio_rate = 48e3

        ##################################################
        # Blocks
        ##################################################

        # Create the options list
        self._tau_options = [5e-05, 7.5e-05]
        # Create the labels list
        self._tau_labels = ['50 us', '75 us']
        # Create the combo box
        self._tau_tool_bar = Qt.QToolBar(self)
        self._tau_tool_bar.addWidget(Qt.QLabel("De-emphasis" + ": "))
        self._tau_combo_box = Qt.QComboBox()
        self._tau_tool_bar.addWidget(self._tau_combo_box)
        for _label in self._tau_labels: self._tau_combo_box.addItem(_label)
        self._tau_callback = lambda i: Qt.QMetaObject.invokeMethod(self._tau_combo_box, "setCurrentIndex", Qt.Q_ARG("int", self._tau_options.index(i)))
        self._tau_callback(self.tau)
        self._tau_combo_box.currentIndexChanged.connect(
            lambda i: self.set_tau(self._tau_options[i]))
        # Create the radio buttons
        self.top_layout.addWidget(self._tau_tool_bar)
        self._rf_gain_range = qtgui.Range(0, 49.6, 0.1, 20.7, 200)
        self._rf_gain_win = qtgui.RangeWidget(self._rf_gain_range, self.set_rf_gain, "RF gain (dB)", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._rf_gain_win)
        _rec_check_box = Qt.QCheckBox("Record I/Q")
        self._rec_choices = {True: True, False: False}
        self._rec_choices_inv = dict((v,k) for k,v in self._rec_choices.items())
        self._rec_callback = lambda i: Qt.QMetaObject.invokeMethod(_rec_check_box, "setChecked", Qt.Q_ARG("bool", self._rec_choices_inv[i]))
        self._rec_callback(self.rec)
        _rec_check_box.stateChanged.connect(lambda i: self.set_rec(self._rec_choices[bool(i)]))
        self.top_layout.addWidget(_rec_check_box)
        self._pll_bw_range = qtgui.Range(0.005, 0.6, 0.005, 0.05, 200)
        self._pll_bw_win = qtgui.RangeWidget(self._pll_bw_range, self.set_pll_bw, "PLL loop bandwidth (rad/sample)", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._pll_bw_win)
        self._fc_range = qtgui.Range(24e6, 1766e6, 100e3, 98.0e6, 200)
        self._fc_win = qtgui.RangeWidget(self._fc_range, self.set_fc, "Signal frequency fc (Hz)", "counter", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._fc_win)
        self._f_m_range = qtgui.Range(300, 15e3, 100, 1e3, 200)
        self._f_m_win = qtgui.RangeWidget(self._f_m_range, self.set_f_m, "Test tone f_m (Hz)", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._f_m_win)
        self._f_fine_range = qtgui.Range(-30e3, 30e3, 10, 0, 200)
        self._f_fine_win = qtgui.RangeWidget(self._f_fine_range, self.set_f_fine, "Fine tuning (Hz)", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._f_fine_win)
        self._dev_range = qtgui.Range(1e3, 75e3, 500, 75e3, 200)
        self._dev_win = qtgui.RangeWidget(self._dev_range, self.set_dev, "Deviation (Hz)", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._dev_win)
        # Create the options list
        self._det_options = [0, 1]
        # Create the labels list
        self._det_labels = ['Quadrature Demod (non-coherent)', 'PLL (coherent)']
        # Create the combo box
        self._det_tool_bar = Qt.QToolBar(self)
        self._det_tool_bar.addWidget(Qt.QLabel("Detector" + ": "))
        self._det_combo_box = Qt.QComboBox()
        self._det_tool_bar.addWidget(self._det_combo_box)
        for _label in self._det_labels: self._det_combo_box.addItem(_label)
        self._det_callback = lambda i: Qt.QMetaObject.invokeMethod(self._det_combo_box, "setCurrentIndex", Qt.Q_ARG("int", self._det_options.index(i)))
        self._det_callback(self.det)
        self._det_combo_box.currentIndexChanged.connect(
            lambda i: self.set_det(self._det_options[i]))
        # Create the radio buttons
        self.top_layout.addWidget(self._det_tool_bar)
        # Create the options list
        self._audio_bw_options = [3000.0, 15000.0]
        # Create the labels list
        self._audio_bw_labels = ['3 kHz (voice)', '15 kHz (broadcast)']
        # Create the combo box
        self._audio_bw_tool_bar = Qt.QToolBar(self)
        self._audio_bw_tool_bar.addWidget(Qt.QLabel("Audio bandwidth" + ": "))
        self._audio_bw_combo_box = Qt.QComboBox()
        self._audio_bw_tool_bar.addWidget(self._audio_bw_combo_box)
        for _label in self._audio_bw_labels: self._audio_bw_combo_box.addItem(_label)
        self._audio_bw_callback = lambda i: Qt.QMetaObject.invokeMethod(self._audio_bw_combo_box, "setCurrentIndex", Qt.Q_ARG("int", self._audio_bw_options.index(i)))
        self._audio_bw_callback(self.audio_bw)
        self._audio_bw_combo_box.currentIndexChanged.connect(
            lambda i: self.set_audio_bw(self._audio_bw_options[i]))
        # Create the radio buttons
        self.top_layout.addWidget(self._audio_bw_tool_bar)
        self._volume_range = qtgui.Range(0, 1, 0.01, 0.3, 200)
        self._volume_win = qtgui.RangeWidget(self._volume_range, self.set_volume, "Volume", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._volume_win)
        self.vol = blocks.multiply_const_ff(volume)
        self.tot_rms = blocks.rms_ff((2e-4))
        self.tot_log = blocks.nlog10_ff(20, 1, 0)
        self.sinad_sub = blocks.sub_ff(1)
        self.sinad_num = qtgui.number_sink(
            gr.sizeof_float,
            0,
            qtgui.NUM_GRAPH_HORIZ,
            1,
            None # parent
        )
        self.sinad_num.set_update_time(0.10)
        self.sinad_num.set_title("SINAD (dB)")

        labels = ['', '', '', '', '',
            '', '', '', '', '']
        units = ['dB', '', '', '', '',
            '', '', '', '', '']
        colors = [("black", "black"), ("black", "black"), ("black", "black"), ("black", "black"), ("black", "black"),
            ("black", "black"), ("black", "black"), ("black", "black"), ("black", "black"), ("black", "black")]
        factor = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]

        for i in range(1):
            self.sinad_num.set_min(i, 0)
            self.sinad_num.set_max(i, 70)
            self.sinad_num.set_color(i, colors[i][0], colors[i][1])
            if len(labels[i]) == 0:
                self.sinad_num.set_label(i, "Data {0}".format(i))
            else:
                self.sinad_num.set_label(i, labels[i])
            self.sinad_num.set_unit(i, units[i])
            self.sinad_num.set_factor(i, factor[i])

        self.sinad_num.enable_autoscale(False)
        self._sinad_num_win = sip.wrapinstance(self.sinad_num.qwidget(), Qt.QWidget)
        self.top_layout.addWidget(self._sinad_num_win)
        self.rf_spec = qtgui.freq_sink_c(
            1024, #size
            window.WIN_BLACKMAN_hARRIS, #wintype
            fc, #fc
            quad_rate, #bw
            "Channel spectrum (240 kHz)", #name
            1,
            None # parent
        )
        self.rf_spec.set_update_time(0.10)
        self.rf_spec.set_y_axis((-120), 0)
        self.rf_spec.set_y_label('Relative Gain', 'dB')
        self.rf_spec.set_trigger_mode(qtgui.TRIG_MODE_FREE, 0.0, 0, "")
        self.rf_spec.enable_autoscale(False)
        self.rf_spec.enable_grid(True)
        self.rf_spec.set_fft_average(0.1)
        self.rf_spec.enable_axis_labels(True)
        self.rf_spec.enable_control_panel(True)
        self.rf_spec.set_fft_window_normalized(False)



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
                self.rf_spec.set_line_label(i, "Data {0}".format(i))
            else:
                self.rf_spec.set_line_label(i, labels[i])
            self.rf_spec.set_line_width(i, widths[i])
            self.rf_spec.set_line_color(i, colors[i])
            self.rf_spec.set_line_alpha(i, alphas[i])

        self._rf_spec_win = sip.wrapinstance(self.rf_spec.qwidget(), Qt.QWidget)
        self.top_layout.addWidget(self._rf_spec_win)
        self.recorder = recorder.blk(team=team, lab=2, fc=fc, fs=quad_rate, gain=rf_gain, record=rec, max_seconds=30.0, folder='.')
        self.quad_demod = analog.quadrature_demod_cf((quad_rate/(2*math.pi*dev)))
        self.pll_scale = blocks.multiply_const_ff((quad_rate/(2*math.pi*dev)))
        self.pll_det = analog.pll_freqdet_cf(pll_bw, (min(2*math.pi*1.5*dev/quad_rate, 3.0)), (-min(2*math.pi*1.5*dev/quad_rate, 3.0)))
        self.pch_rms = blocks.rms_cf((2e-5))
        self.pch_num = qtgui.number_sink(
            gr.sizeof_float,
            0,
            qtgui.NUM_GRAPH_HORIZ,
            1,
            None # parent
        )
        self.pch_num.set_update_time(0.10)
        self.pch_num.set_title("Channel power (dBFS)")

        labels = ['', '', '', '', '',
            '', '', '', '', '']
        units = ['dB', '', '', '', '',
            '', '', '', '', '']
        colors = [("black", "black"), ("black", "black"), ("black", "black"), ("black", "black"), ("black", "black"),
            ("black", "black"), ("black", "black"), ("black", "black"), ("black", "black"), ("black", "black")]
        factor = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]

        for i in range(1):
            self.pch_num.set_min(i, -100)
            self.pch_num.set_max(i, 0)
            self.pch_num.set_color(i, colors[i][0], colors[i][1])
            if len(labels[i]) == 0:
                self.pch_num.set_label(i, "Data {0}".format(i))
            else:
                self.pch_num.set_label(i, labels[i])
            self.pch_num.set_unit(i, units[i])
            self.pch_num.set_factor(i, factor[i])

        self.pch_num.enable_autoscale(False)
        self._pch_num_win = sip.wrapinstance(self.pch_num.qwidget(), Qt.QWidget)
        self.top_layout.addWidget(self._pch_num_win)
        self.pch_log = blocks.nlog10_ff(20, 1, 0)
        self.offset_num = qtgui.number_sink(
            gr.sizeof_float,
            0,
            qtgui.NUM_GRAPH_HORIZ,
            1,
            None # parent
        )
        self.offset_num.set_update_time(0.10)
        self.offset_num.set_title("Carrier frequency offset (Hz)")

        labels = ['', '', '', '', '',
            '', '', '', '', '']
        units = ['Hz', '', '', '', '',
            '', '', '', '', '']
        colors = [("black", "black"), ("black", "black"), ("black", "black"), ("black", "black"), ("black", "black"),
            ("black", "black"), ("black", "black"), ("black", "black"), ("black", "black"), ("black", "black")]
        factor = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]

        for i in range(1):
            self.offset_num.set_min(i, -20000)
            self.offset_num.set_max(i, 20000)
            self.offset_num.set_color(i, colors[i][0], colors[i][1])
            if len(labels[i]) == 0:
                self.offset_num.set_label(i, "Data {0}".format(i))
            else:
                self.offset_num.set_label(i, labels[i])
            self.offset_num.set_unit(i, units[i])
            self.offset_num.set_factor(i, factor[i])

        self.offset_num.enable_autoscale(False)
        self._offset_num_win = sip.wrapinstance(self.offset_num.qwidget(), Qt.QWidget)
        self.top_layout.addWidget(self._offset_num_win)
        self.offset_hz = blocks.multiply_const_ff(dev)
        self.offset_avg = filter.single_pole_iir_filter_ff((2e-5), 1)
        self.notch = filter.fir_filter_fff(
            1,
            firdes.band_reject(
                1,
                audio_rate,
                (f_m - 300),
                (f_m + 300),
                200,
                window.WIN_HAMMING,
                6.76))
        self.nd_rms = blocks.rms_ff((2e-4))
        self.nd_log = blocks.nlog10_ff(20, 1, 0)
        self.iio_pluto_source_0 = iio.fmcomms2_source_fc32('192.168.1.10' if '192.168.1.10' else iio.get_pluto_uri(), [True, True], 32768)
        self.iio_pluto_source_0.set_len_tag_key('packet_len')
        self.iio_pluto_source_0.set_frequency((int(fc - f_off)))
        self.iio_pluto_source_0.set_samplerate(int(samp_rate))
        self.iio_pluto_source_0.set_gain_mode(0, 'manual')
        self.iio_pluto_source_0.set_gain(0, rf_gain)
        self.iio_pluto_source_0.set_quadrature(True)
        self.iio_pluto_source_0.set_rfdc(True)
        self.iio_pluto_source_0.set_bbdc(True)
        self.iio_pluto_source_0.set_filter_params('Auto', '', 0, 0)
        self.det_spec = qtgui.freq_sink_f(
            4096, #size
            window.WIN_BLACKMAN_hARRIS, #wintype
            0, #fc
            quad_rate, #bw
            "Detector outputs", #name
            2,
            None # parent
        )
        self.det_spec.set_update_time(0.10)
        self.det_spec.set_y_axis((-120), 0)
        self.det_spec.set_y_label('Relative Gain', 'dB')
        self.det_spec.set_trigger_mode(qtgui.TRIG_MODE_FREE, 0.0, 0, "")
        self.det_spec.enable_autoscale(False)
        self.det_spec.enable_grid(True)
        self.det_spec.set_fft_average(0.1)
        self.det_spec.enable_axis_labels(True)
        self.det_spec.enable_control_panel(True)
        self.det_spec.set_fft_window_normalized(False)


        self.det_spec.set_plot_pos_half(not True)

        labels = ['Quadrature Demod', 'PLL', '', '', '',
            '', '', '', '', '']
        widths = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        colors = ["blue", "red", "green", "black", "cyan",
            "magenta", "yellow", "dark red", "dark green", "dark blue"]
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0, 1.0]

        for i in range(2):
            if len(labels[i]) == 0:
                self.det_spec.set_line_label(i, "Data {0}".format(i))
            else:
                self.det_spec.set_line_label(i, labels[i])
            self.det_spec.set_line_width(i, widths[i])
            self.det_spec.set_line_color(i, colors[i])
            self.det_spec.set_line_alpha(i, alphas[i])

        self._det_spec_win = sip.wrapinstance(self.det_spec.qwidget(), Qt.QWidget)
        self.top_layout.addWidget(self._det_spec_win)
        self.det_select = blocks.selector(gr.sizeof_float*1,det,0)
        self.det_select.set_enabled(True)
        self.deemph = analog.fm_deemph(fs=audio_rate, tau=tau)
        self.dc_block = filter.dc_blocker_ff(512, True)
        self.chan_xlate = filter.freq_xlating_fir_filter_ccc(10, firdes.low_pass(1, samp_rate, 100e3, 20e3), (f_off + f_fine), samp_rate)
        self.chan_filter = filter.fir_filter_ccf(
            1,
            firdes.low_pass(
                1,
                quad_rate,
                (chan_bw/2),
                (chan_bw/8),
                window.WIN_HAMMING,
                6.76))
        self.audio_spec = qtgui.freq_sink_f(
            4096, #size
            window.WIN_BLACKMAN_hARRIS, #wintype
            0, #fc
            audio_rate, #bw
            "Audio spectrum (48 kHz)", #name
            1,
            None # parent
        )
        self.audio_spec.set_update_time(0.10)
        self.audio_spec.set_y_axis((-120), 0)
        self.audio_spec.set_y_label('Relative Gain', 'dB')
        self.audio_spec.set_trigger_mode(qtgui.TRIG_MODE_FREE, 0.0, 0, "")
        self.audio_spec.enable_autoscale(False)
        self.audio_spec.enable_grid(True)
        self.audio_spec.set_fft_average(0.1)
        self.audio_spec.enable_axis_labels(True)
        self.audio_spec.enable_control_panel(True)
        self.audio_spec.set_fft_window_normalized(False)


        self.audio_spec.set_plot_pos_half(not True)

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
                self.audio_spec.set_line_label(i, "Data {0}".format(i))
            else:
                self.audio_spec.set_line_label(i, labels[i])
            self.audio_spec.set_line_width(i, widths[i])
            self.audio_spec.set_line_color(i, colors[i])
            self.audio_spec.set_line_alpha(i, alphas[i])

        self._audio_spec_win = sip.wrapinstance(self.audio_spec.qwidget(), Qt.QWidget)
        self.top_layout.addWidget(self._audio_spec_win)
        self.audio_out = audio.sink(48000, '', True)
        self.audio_lpf = filter.fir_filter_fff(
            5,
            firdes.low_pass(
                1,
                quad_rate,
                audio_bw,
                (0.25*audio_bw + 250),
                window.WIN_HAMMING,
                6.76))


        ##################################################
        # Connections
        ##################################################
        self.connect((self.audio_lpf, 0), (self.dc_block, 0))
        self.connect((self.chan_filter, 0), (self.pch_rms, 0))
        self.connect((self.chan_filter, 0), (self.pll_det, 0))
        self.connect((self.chan_filter, 0), (self.quad_demod, 0))
        self.connect((self.chan_filter, 0), (self.rf_spec, 0))
        self.connect((self.chan_xlate, 0), (self.chan_filter, 0))
        self.connect((self.chan_xlate, 0), (self.recorder, 0))
        self.connect((self.dc_block, 0), (self.audio_spec, 0))
        self.connect((self.dc_block, 0), (self.deemph, 0))
        self.connect((self.dc_block, 0), (self.notch, 0))
        self.connect((self.dc_block, 0), (self.tot_rms, 0))
        self.connect((self.deemph, 0), (self.vol, 0))
        self.connect((self.det_select, 0), (self.audio_lpf, 0))
        self.connect((self.iio_pluto_source_0, 0), (self.chan_xlate, 0))
        self.connect((self.nd_log, 0), (self.sinad_sub, 1))
        self.connect((self.nd_rms, 0), (self.nd_log, 0))
        self.connect((self.notch, 0), (self.nd_rms, 0))
        self.connect((self.offset_avg, 0), (self.offset_hz, 0))
        self.connect((self.offset_hz, 0), (self.offset_num, 0))
        self.connect((self.pch_log, 0), (self.pch_num, 0))
        self.connect((self.pch_rms, 0), (self.pch_log, 0))
        self.connect((self.pll_det, 0), (self.pll_scale, 0))
        self.connect((self.pll_scale, 0), (self.det_select, 1))
        self.connect((self.pll_scale, 0), (self.det_spec, 1))
        self.connect((self.quad_demod, 0), (self.det_select, 0))
        self.connect((self.quad_demod, 0), (self.det_spec, 0))
        self.connect((self.quad_demod, 0), (self.offset_avg, 0))
        self.connect((self.sinad_sub, 0), (self.sinad_num, 0))
        self.connect((self.tot_log, 0), (self.sinad_sub, 0))
        self.connect((self.tot_rms, 0), (self.tot_log, 0))
        self.connect((self.vol, 0), (self.audio_out, 0))


    def closeEvent(self, event):
        self.settings = Qt.QSettings("gnuradio/flowgraphs", "lab02_fm_rx")
        self.settings.setValue("geometry", self.saveGeometry())
        self.stop()
        self.wait()

        event.accept()

    def get_dev(self):
        return self.dev

    def set_dev(self, dev):
        self.dev = dev
        self.set_chan_bw(min(2*(self.dev + self.audio_bw), 200e3))
        self.offset_hz.set_k(self.dev)
        self.pll_det.set_max_freq((min(2*math.pi*1.5*self.dev/self.quad_rate, 3.0)))
        self.pll_det.set_min_freq((-min(2*math.pi*1.5*self.dev/self.quad_rate, 3.0)))
        self.pll_scale.set_k((self.quad_rate/(2*math.pi*self.dev)))
        self.quad_demod.set_gain((self.quad_rate/(2*math.pi*self.dev)))

    def get_audio_bw(self):
        return self.audio_bw

    def set_audio_bw(self, audio_bw):
        self.audio_bw = audio_bw
        self._audio_bw_callback(self.audio_bw)
        self.set_chan_bw(min(2*(self.dev + self.audio_bw), 200e3))
        self.audio_lpf.set_taps(firdes.low_pass(1, self.quad_rate, self.audio_bw, (0.25*self.audio_bw + 250), window.WIN_HAMMING, 6.76))

    def get_volume(self):
        return self.volume

    def set_volume(self, volume):
        self.volume = volume
        self.vol.set_k(self.volume)

    def get_team(self):
        return self.team

    def set_team(self, team):
        self.team = team
        self.recorder.team = self.team

    def get_tau(self):
        return self.tau

    def set_tau(self, tau):
        self.tau = tau
        self._tau_callback(self.tau)

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.chan_xlate.set_taps(firdes.low_pass(1, self.samp_rate, 100e3, 20e3))
        self.iio_pluto_source_0.set_samplerate(int(self.samp_rate))

    def get_rf_gain(self):
        return self.rf_gain

    def set_rf_gain(self, rf_gain):
        self.rf_gain = rf_gain
        self.iio_pluto_source_0.set_gain(0, self.rf_gain)
        self.recorder.gain = self.rf_gain

    def get_rec(self):
        return self.rec

    def set_rec(self, rec):
        self.rec = rec
        self._rec_callback(self.rec)
        self.recorder.record = self.rec

    def get_quad_rate(self):
        return self.quad_rate

    def set_quad_rate(self, quad_rate):
        self.quad_rate = quad_rate
        self.audio_lpf.set_taps(firdes.low_pass(1, self.quad_rate, self.audio_bw, (0.25*self.audio_bw + 250), window.WIN_HAMMING, 6.76))
        self.chan_filter.set_taps(firdes.low_pass(1, self.quad_rate, (self.chan_bw/2), (self.chan_bw/8), window.WIN_HAMMING, 6.76))
        self.det_spec.set_frequency_range(0, self.quad_rate)
        self.pll_det.set_max_freq((min(2*math.pi*1.5*self.dev/self.quad_rate, 3.0)))
        self.pll_det.set_min_freq((-min(2*math.pi*1.5*self.dev/self.quad_rate, 3.0)))
        self.pll_scale.set_k((self.quad_rate/(2*math.pi*self.dev)))
        self.quad_demod.set_gain((self.quad_rate/(2*math.pi*self.dev)))
        self.recorder.fs = self.quad_rate
        self.rf_spec.set_frequency_range(self.fc, self.quad_rate)

    def get_ppm(self):
        return self.ppm

    def set_ppm(self, ppm):
        self.ppm = ppm

    def get_pll_bw(self):
        return self.pll_bw

    def set_pll_bw(self, pll_bw):
        self.pll_bw = pll_bw
        self.pll_det.set_loop_bandwidth(self.pll_bw)

    def get_fc(self):
        return self.fc

    def set_fc(self, fc):
        self.fc = fc
        self.iio_pluto_source_0.set_frequency((int(self.fc - self.f_off)))
        self.recorder.fc = self.fc
        self.rf_spec.set_frequency_range(self.fc, self.quad_rate)

    def get_f_off(self):
        return self.f_off

    def set_f_off(self, f_off):
        self.f_off = f_off
        self.chan_xlate.set_center_freq((self.f_off + self.f_fine))
        self.iio_pluto_source_0.set_frequency((int(self.fc - self.f_off)))

    def get_f_m(self):
        return self.f_m

    def set_f_m(self, f_m):
        self.f_m = f_m
        self.notch.set_taps(firdes.band_reject(1, self.audio_rate, (self.f_m - 300), (self.f_m + 300), 200, window.WIN_HAMMING, 6.76))

    def get_f_fine(self):
        return self.f_fine

    def set_f_fine(self, f_fine):
        self.f_fine = f_fine
        self.chan_xlate.set_center_freq((self.f_off + self.f_fine))

    def get_det(self):
        return self.det

    def set_det(self, det):
        self.det = det
        self._det_callback(self.det)
        self.det_select.set_input_index(self.det)

    def get_chan_bw(self):
        return self.chan_bw

    def set_chan_bw(self, chan_bw):
        self.chan_bw = chan_bw
        self.chan_filter.set_taps(firdes.low_pass(1, self.quad_rate, (self.chan_bw/2), (self.chan_bw/8), window.WIN_HAMMING, 6.76))

    def get_audio_rate(self):
        return self.audio_rate

    def set_audio_rate(self, audio_rate):
        self.audio_rate = audio_rate
        self.audio_spec.set_frequency_range(0, self.audio_rate)
        self.notch.set_taps(firdes.band_reject(1, self.audio_rate, (self.f_m - 300), (self.f_m + 300), 200, window.WIN_HAMMING, 6.76))




def main(top_block_cls=lab02_fm_rx, options=None):

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
