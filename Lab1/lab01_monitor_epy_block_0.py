import os
import datetime
import numpy as np
from gnuradio import gr


class blk(gr.sync_block):
    """
    SDR Lab IQ Recorder
    ضبط داده خام I/Q با فرمت استاندارد آزمایشگاه:
    teamID_labNN_fc_fs_gain_timestamp.cf32
    """

    def __init__(
        self,
        team_id="Team-07",
        lab_id="lab01",
        fc=945000000,
        fs=2600000,
        gain=20.0,
        record=False,
        max_seconds=3.8,
        out_dir=".",
    ):
        gr.sync_block.__init__(
            self,
            name="SDR Lab IQ Recorder",
            in_sig=[np.complex64],
            out_sig=None,
        )

        # ذخیره پارامترهای اولیه
        self._team_id = str(team_id)
        self._lab_id = str(lab_id)
        self._fc = fc
        self._fs = fs
        self._gain = gain
        self._record = bool(record)
        self._max_seconds = float(max_seconds)
        self._out_dir = str(out_dir)

        # متغیرهای وضعیت ضبط
        self._file = None
        self._filename = ""
        self._samples_written = 0
        self._max_samples = 0
        self._locked_until_uncheck = False

    def _open_new_file(self):
        """باز کردن یک فایل جدید با نام استاندارد آزمایشگاه"""
        if not os.path.exists(self._out_dir):
            os.makedirs(self._out_dir, exist_ok=True)

        timestamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
        fname = f"{self._team_id}_{self._lab_id}_{int(self._fc)}_{int(self._fs)}_{float(self._gain):.1f}_{timestamp}.cf32"
        self._filename = os.path.join(self._out_dir, fname)

        self._file = open(self._filename, "wb")
        self._samples_written = 0
        self._max_samples = int(round(self._max_seconds * self._fs))

        print(
            f"[REC] Started recording: {self._filename} (Max limit: {self._max_seconds:.2f} s)"
        )

    def _close_file(self, reason=""):
        """بستن فایل فعلی و چاپ گزارش در کنسول"""
        if self._file is not None:
            self._file.close()
            self._file = None
            duration = (
                self._samples_written / float(self._fs) if self._fs > 0 else 0.0
            )
            size_mb = (self._samples_written * 8) / (1024 * 1024)
            msg = f" | Reason: {reason}" if reason else ""
            print(
                f"[REC] Closed file: {self._filename} | Duration: {duration:.2f} s ({size_mb:.2f} MB){msg}"
            )

    # --- متدهای ارتباط با متغیرهای GRC (Callback Setters) ---

    @property
    def team_id(self):
        return self._team_id

    @team_id.setter
    def team_id(self, val):
        self._team_id = str(val)

    @property
    def lab_id(self):
        return self._lab_id

    @lab_id.setter
    def lab_id(self, val):
        self._lab_id = str(val)

    @property
    def fc(self):
        return self._fc

    @fc.setter
    def fc(self, val):
        if self._fc != val:
            self._fc = val
            if self._file is not None:
                self._close_file(
                    "Center frequency (fc) changed during recording"
                )
                self._locked_until_uncheck = True

    @property
    def fs(self):
        return self._fs

    @fs.setter
    def fs(self, val):
        if self._fs != val:
            if self._file is not None:
                self._close_file("Sample rate (fs) changed during recording")
                self._locked_until_uncheck = True
            self._fs = val

    @property
    def gain(self):
        return self._gain

    @gain.setter
    def gain(self, val):
        if self._gain != val:
            self._gain = val
            if self._file is not None:
                self._close_file("Gain changed during recording")
                self._locked_until_uncheck = True

    @property
    def record(self):
        return self._record

    @record.setter
    def record(self, val):
        val_bool = bool(val)
        if not val_bool:
            # وقتی کاربر تیک Record را برمی‌دارد
            if self._file is not None:
                self._close_file("User unchecked Record I/Q")
            self._locked_until_uncheck = False
        self._record = val_bool

    @property
    def max_seconds(self):
        return self._max_seconds

    @max_seconds.setter
    def max_seconds(self, val):
        self._max_seconds = float(val)
        if self._file is not None:
            self._max_samples = int(round(self._max_seconds * self._fs))

    @property
    def out_dir(self):
        return self._out_dir

    @out_dir.setter
    def out_dir(self, val):
        self._out_dir = str(val)

    # --- حلقه اصلی پردازش نمونه‌ها ---

    def work(self, input_items, output_items):
        in0 = input_items[0]
        n_in = len(in0)

        if self._record and not self._locked_until_uncheck:
            # اگر تازه تیک زده شده، فایل جدید باز کن
            if self._file is None:
                self._open_new_file()

            # بررسی سقف مجاز نمونه‌ها طبق rec_sec
            remaining = self._max_samples - self._samples_written
            if remaining <= 0:
                self._close_file(f"Reached max duration ({self._max_seconds}s)")
                self._locked_until_uncheck = True
            else:
                to_write = min(n_in, remaining)
                # ذخیره با فرمت استاندارد cf32 (8 بایت به ازای هر نمونه: 4 بایت I و 4 بایت Q)
                in0[:to_write].tofile(self._file)
                self._samples_written += to_write

                if self._samples_written >= self._max_samples:
                    self._close_file(
                        f"Reached max duration ({self._max_seconds}s)"
                    )
                    self._locked_until_uncheck = True

        return n_in

    def stop(self):
        """بستن ایمن فایل در صورت توقف فلوگراف"""
        if self._file is not None:
            self._close_file("Flowgraph stopped")
        return True