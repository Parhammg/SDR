"""Reproduce Team 01's offline spectrum measurements from the .cf32 archive."""

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import re

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FormatStrFormatter, MaxNLocator
import numpy as np
from scipy import fft, ndimage, signal


ROOT = Path(__file__).resolve().parent
FILE_PATTERN = re.compile(r'.+_lab01_(\d+)_(\d+)_([\d.]+)_(\d{8}T\d{6})\.cf32')
STYLE = {'axes.spines.top': False, 'axes.spines.right': False, 'axes.grid': True,
         'grid.alpha': .22, 'axes.labelsize': 9, 'axes.titlesize': 10,
         'font.size': 9, 'figure.facecolor': 'white', 'savefig.facecolor': 'white'}
BLUE, ORANGE, GREEN = '#15638c', '#b35026', '#0a7569'


@dataclass(frozen=True)
class Capture:
    path: Path
    center: int
    rate: int
    gain: float
    timestamp: str

    @classmethod
    def read(cls, path):
        center, rate, gain, timestamp = FILE_PATTERN.fullmatch(path.name).groups()
        if path.stat().st_size % 8:
            raise ValueError(f'Partial complex64 sample in {path.name}')
        return cls(path, int(center), int(rate), float(gain), timestamp)

    @property
    def count(self):
        return self.path.stat().st_size // 8

    def samples(self):
        return np.memmap(self.path, mode='r', dtype='<c8')


def db(power):
    return 10 * np.log10(np.maximum(power, 1e-24))


def frame_power(capture, n, hop, *, window='hann', keep_tail=False):
    """Return coherent-gain-normalized two-sided power for each FFT frame."""
    x = capture.samples()
    starts = np.arange(0, len(x) if keep_tail else len(x) - n + 1, hop)
    weights = signal.get_window(window, n).astype('f4')
    power = np.empty((len(starts), n), dtype='f4')
    frames = np.lib.stride_tricks.sliding_window_view(x, n)[::hop]
    for index in range(0, len(frames), 64):
        part = frames[index:index + 64]
        spectra = fft.fftshift(fft.fft(part * weights, axis=1), axes=1)
        power[index:index + len(part)] = abs(spectra / weights.sum()) ** 2
    if len(starts) > len(frames):
        assert keep_tail and n == hop
        tail = x[starts[-1]:]
        w = weights[:len(tail)]
        power[-1] = abs(fft.fftshift(fft.fft(tail * w, n)) / w.sum()) ** 2
    enbw = capture.rate * np.sum(weights ** 2) / weights.sum() ** 2
    frequencies = capture.center + fft.fftshift(fft.fftfreq(n, 1 / capture.rate))
    return frequencies, starts, power, enbw


def channel(frequency, center, halfwidth):
    return abs(frequency - center) <= halfwidth


def runs(mask):
    changes = np.diff(mask.astype(int), prepend=0, append=0)
    return np.flatnonzero(changes == 1), np.flatnonzero(changes == -1)


def occupied_bandwidth(frequency, psd, floor, center, halfwidth):
    inside = channel(frequency, center, halfwidth)
    f = frequency[inside]
    excess = np.maximum((psd - floor)[inside], 0)
    if excess.sum() <= 0:
        raise ValueError(f'No positive channel power around {center} Hz')
    df = f[1] - f[0]
    cdf = np.r_[0, np.cumsum(excess, dtype='f8') / excess.sum(dtype='f8')]
    return np.interp([.005, .995], cdf, np.r_[f - df / 2, f[-1] + df / 2])


def max_hold_edges(frequency, peak_power, center, search_halfwidth, floor):
    smoothed = db(ndimage.uniform_filter1d(peak_power, size=3))
    selection = np.flatnonzero(channel(frequency, center, search_halfwidth))
    lo, hi = selection[[0, -1]]
    peak = float(smoothed[lo:hi + 1].max())
    x = 20 if peak - floor >= 26 else 6
    level = peak - x
    hits = np.flatnonzero(smoothed[lo:hi + 1] >= level) + lo
    first, last = hits[[0, -1]]
    fleft = np.interp(level, smoothed[first - 1:first + 1], frequency[first - 1:first + 1])
    fright = np.interp(level, smoothed[last:last + 2][::-1], frequency[last:last + 2][::-1])
    return peak, x, fleft, fright, bool(first == lo or last == hi), smoothed


def remote_timing(capture, output):
    n = 4096
    f, starts, power, _ = frame_power(capture, n, n, keep_tail=True)
    inside = channel(f, 433.935e6, 25e3)
    p = db(power[:, inside].sum(axis=1))
    quiet = np.median(p[starts < .3 * capture.rate])
    threshold = quiet + 13
    begin, end = runs(p > threshold)
    valid = (end - begin >= np.ceil(.012 * capture.rate / n)) & (end < len(starts))
    begin, end = begin[valid], end[valid]
    lengths = (end - begin) * n / capture.rate
    periods = np.diff(begin) * n / capture.rate

    # Pool adjacent rows only for plotting. Detection uses every unpooled row.
    show = channel(f, 433.935e6, 57e3)
    group = 2
    merged = np.maximum.reduceat(power[:, show], np.arange(0, len(starts), group), axis=0)
    time = np.r_[starts[::group], capture.count] / capture.rate
    freq = f[show] / 1e6
    freq_edges = np.r_[freq - (freq[1] - freq[0]) / 2, freq[-1] + (freq[1] - freq[0]) / 2]
    fig, axs = plt.subplots(1, 2, figsize=(10.6, 3.3), layout='constrained',
                            gridspec_kw={'width_ratios': [1, 1.15]})
    image = axs[0].pcolormesh(freq_edges, time, db(merged), shading='flat',
                              cmap='viridis', vmin=-100, vmax=-35, rasterized=True)
    axs[0].grid(False)
    axs[0].set(xlabel='RF label (MHz)', ylabel='Time from first sample (s)',
               title='Band B  |  Full 3.846 s recording')
    fig.colorbar(image, ax=axs[0], label='FFT level (dBFS)')
    clip = np.searchsorted(start_times := starts / capture.rate, [.34, .58])
    axs[1].plot(start_times[clip[0]:clip[1]], p[clip[0]:clip[1]], color=BLUE, lw=.9)
    axs[1].axhline(threshold, color=ORANGE, ls='--', lw=.9, label='Burst threshold')
    for a, b in zip(begin, end):
        if .34 < start_times[a] < .58:
            axs[1].axvspan(start_times[a], start_times[b], color=GREEN, alpha=.1, lw=0)
    axs[1].set(xlim=(.34, .58), xlabel='Time from first sample (s)',
               ylabel='In-channel FFT sum (dBFS)', title='Repeated packets  |  First 240 ms of activity')
    axs[1].legend(loc='lower right', fontsize=8)
    fig.savefig(output / 'lab01_keyfob_timing.png', dpi=180)
    plt.close(fig)
    return {
        'count': len(begin), 'starts_s': start_times[begin].tolist(),
        'ends_s': start_times[end].tolist(), 'duration_ms': float(1000 * np.median(lengths)),
        'duration_range_ms': (1000 * np.quantile(lengths, [.05, .95])).tolist(),
        'period_ms': float(1000 * np.median(periods)),
        'period_range_ms': (1000 * np.quantile(periods, [.05, .95])).tolist(),
        'resolution_ms': 1000 * n / capture.rate, 'threshold_dbfs': float(threshold),
    }


def gsm_frequency_reference(capture):
    """Detect GSM frequency-correction bursts by narrow-tone concentration."""
    n = 1024
    f, starts, power, _ = frame_power(capture, n, n // 2)
    tones = []
    fcch_offset = (1625e3 / 6) / 4
    for nominal, concentration in [(951.8e6, .27), (952.2e6, .35), (952.8e6, .54)]:
        fcch = nominal + fcch_offset
        target = np.flatnonzero(channel(f, fcch, 13e3))
        local = channel(f, fcch, 42e3)
        peaks = target[np.argmax(power[:, target], axis=1)]
        row = np.arange(len(starts))
        height = power[row, peaks]
        ratio = height / power[:, local].sum(axis=1)
        # Retain the highest-concentration row for each distinct pulse.
        begin, end = runs(ratio > concentration)
        chosen = np.array([i + np.argmax(ratio[i:j]) for i, j in zip(begin, end)])
        p = db(power[chosen[:, None], peaks[chosen, None] + np.arange(-1, 2)])
        offset = .5 * (p[:, 0] - p[:, 2]) / (p[:, 0] - 2 * p[:, 1] + p[:, 2])
        estimates = f[peaks[chosen]] + offset * (f[1] - f[0]) - fcch_offset
        center = np.median(estimates)
        stable = abs(estimates - center) < 300
        estimates = estimates[stable]
        times = starts[chosen][stable] / capture.rate
        frame_seconds = .004615384615
        multiframe = 51 * frame_seconds
        offsets = np.arange(0, 50, 10) * frame_seconds
        phases = (times[:, None] - offsets).ravel() % multiframe
        delta = (times[:, None, None] - phases[None, :, None] - offsets + multiframe / 2)
        distance = abs(delta % multiframe - multiframe / 2).min(axis=2)
        on_schedule = distance[:, np.argmax((distance < .00035).sum(axis=0))] < .00035
        estimates, times = estimates[on_schedule], times[on_schedule]
        errors = estimates - nominal
        sigma = 1.4826 * np.median(abs(errors - np.median(errors)))
        repeat = np.diff(times)
        on_grid = (abs(repeat - 10 * frame_seconds) < .0007) | (abs(repeat - 11 * frame_seconds) < .0007)
        tones.append({'nominal_mhz': nominal / 1e6, 'arfcn': round((nominal - 935e6) / 200e3),
                      'center_mhz': float(np.median(estimates) / 1e6),
                      'delta_khz': float(np.median(errors) / 1e3),
                      'ppm': float(np.median(errors) / nominal * 1e6), 'scatter_hz': float(sigma),
                      'pulses': int(len(errors)), 'expected_intervals': int(on_grid.sum())})
    return tones


def measure(capture, config, timing):
    label, nominal, halfwidth, n, gate = config
    f, starts, powers, enbw = frame_power(capture, n, n // 2)
    band = channel(f, nominal, halfwidth)
    dc = abs(f - capture.center) < 4e3
    channel_power = db(powers[:, band & ~dc].sum(axis=1))
    active = np.ones(len(starts), dtype=bool)
    if gate == 'remote':
        times = starts / capture.rate
        begin = np.array(timing['starts_s'])
        end = np.array(timing['ends_s'])
        group = np.searchsorted(begin, times, side='right') - 1
        active = (group >= 0) & (times + n / capture.rate <= end[group])
        off = times + n / capture.rate <= .30
    elif gate is not None:
        active = channel_power >= gate
        off = channel_power <= gate - 10
    else:
        off = None
    if not active.any():
        raise ValueError(f'No usable FFT frames for {label}')

    # Linear average of 50%-overlapped, windowed periodograms is Welch PSD.
    psd = powers[active].mean(axis=0, dtype='f8') / enbw
    peak_power = powers.max(axis=0)
    near = channel(f, nominal, halfwidth * 1.28)
    if np.any(dc & near):
        # DC spur sits on channel #85. Interpolate its bins from adjacent bins.
        psd[dc] = np.interp(f[dc], f[~dc], psd[~dc])
        peak_power[dc] = np.interp(f[dc], f[~dc], peak_power[~dc])
    flank = (abs(f - nominal) >= halfwidth * 1.15) & near
    # For bursts use an off-burst spectrum as the frequency-dependent baseline.
    # Continuous-carrier floor comes from the quieter side of the adjacent bins.
    if off is None:
        floor = min(np.median(psd[flank & (f < nominal)]), np.median(psd[flank & (f > nominal)]))
    else:
        floor = powers[off].mean(axis=0, dtype='f8') / enbw
        floor[dc] = np.interp(f[dc], f[~dc], floor[~dc])
    max_floor = np.percentile(db(peak_power[flank]), 25)
    peak, x, left, right, limited, max_trace = max_hold_edges(f, peak_power, nominal, halfwidth * 1.2, max_floor)
    lower, upper = occupied_bandwidth(f, psd, floor, nominal, halfwidth)
    narrow = np.diff(occupied_bandwidth(f, psd, floor, nominal, .9 * halfwidth))[0]
    wide = np.diff(occupied_bandwidth(f, psd, floor, nominal, 1.1 * halfwidth))[0]
    fsel = f[near] / 1e6
    row = {
        'label': label, 'capture': capture.path.name, 'fs_msps': capture.rate / 1e6,
        'nominal_mhz': nominal / 1e6, 'fft_length': n, 'bin_khz': capture.rate / n / 1e3,
        'x_db': x, 'fL_mhz': float(left / 1e6), 'fU_mhz': float(right / 1e6),
        'center_x_mhz': float((left + right) / 2e6), 'bandwidth_x_khz': float((right - left) / 1e3),
        'peak_dbfs': peak, 'max_floor_dbfs': float(max_floor), 'x_range_limited': limited,
        'center_99_mhz': float((lower + upper) / 2e6), 'bandwidth_99_khz': float((upper - lower) / 1e3),
        'bounds_99_mhz': [float(lower / 1e6), float(upper / 1e6)],
        'b99_window_variation_khz': [float(narrow / 1e3), float(wide / 1e3)],
        'active_fraction_pct': float(100 * np.mean(active)),
        'occupancy_window_khz': 2 * halfwidth / 1e3,
        'channel_p10_p90_dbfs': np.quantile(channel_power, [.1, .9]).tolist(),
    }
    return row, (fsel, db(psd[near]), max_trace[near], enbw)


def signal_figure(rows, traces, output):
    fig, axs = plt.subplots(2, 3, figsize=(11, 5.0), layout='constrained')
    for ax, row, trace in zip(axs.flat, rows, traces):
        f, psd, max_trace, enbw = trace
        ax.plot(f, psd, lw=.9, color=BLUE, label='Welch PSD')
        ax.plot(f, max_trace - db(enbw), lw=.65, color=ORANGE, label='Max Hold / ENBW')
        ax.axvspan(*row['bounds_99_mhz'], color=GREEN, alpha=.15, label='99% OBW')
        ax.set(title=row['label'], xlabel='RF label (MHz)', ylabel='PSD (dBFS/Hz)')
        ax.xaxis.set_major_locator(MaxNLocator(4))
        ax.xaxis.set_major_formatter(FormatStrFormatter('%.3f'))
    axs.flat[-1].axis('off')
    axs.flat[-1].legend(*axs.flat[0].get_legend_handles_labels(), loc='center', frameon=False)
    fig.savefig(output / 'lab01_welch_psds.png', dpi=180)
    plt.close(fig)


def quiet_span(capture):
    f, _, p, enbw = frame_power(capture, 4096, 4096)
    b = (f - capture.center) / capture.rate
    psd = db(p.mean(axis=0, dtype='f8') / enbw)
    ranges = np.arange(-.5, .501, .05)
    noise = [float(np.median(psd[(b >= lo) & (b < hi)])) for lo, hi in zip(ranges[:-1], ranges[1:])]
    reference = float(np.median(noise[4:16]))
    first, last = 9, 10
    while first > 0 and abs(noise[first - 1] - reference) <= 3:
        first -= 1
    while last < len(noise) - 1 and abs(noise[last + 1] - reference) <= 3:
        last += 1
    return {'ratio': float(ranges[last + 1] - ranges[first]), 'range_fs': [float(ranges[first]), float(ranges[last + 1])],
            'center_dbfs_hz': reference, 'edge_dbfs_hz': [noise[0], noise[-1]], 'noise_dbfs_hz': noise}


def survey_figure(captures, output):
    fig, axs = plt.subplots(2, 2, figsize=(10.6, 4.5), layout='constrained')
    surveys = [(914000000, 'Uplink survey  |  20 MS/s'), (943490000, 'Wide block detail  |  2.6 MS/s'),
               (958990000, 'Upper downlink  |  2.6 MS/s'), (967990000, 'Beyond downlink  |  2.6 MS/s')]
    for ax, (center, title) in zip(axs.flat, surveys):
        cap = captures[center]
        f, _, p, enbw = frame_power(cap, 4096, 4096)
        avg = p.mean(axis=0, dtype='f8') / enbw
        max_hold = p.max(axis=0) / enbw
        ax.plot(f / 1e6, db(max_hold), color=ORANGE, lw=.55, label='Max Hold / ENBW')
        ax.plot(f / 1e6, db(avg), color=BLUE, lw=.75, label='Average PSD')
        ax.axvspan((center - .4 * cap.rate) / 1e6, (center + .4 * cap.rate) / 1e6, alpha=.07, color=BLUE)
        ax.set(title=title, xlabel='RF label (MHz)', ylabel='PSD (dBFS/Hz)')
        ax.ticklabel_format(axis='x', style='plain', useOffset=False)
    axs.flat[0].legend(loc='upper right', fontsize=8)
    fig.savefig(output / 'lab01_raw_survey.png', dpi=180)
    plt.close(fig)


def analyze(data, output):
    output.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update(STYLE)
    archive = [Capture.read(p) for p in sorted(data.glob('*_lab01_*.cf32'))]
    captures = {c.center: c for c in archive if c.rate == 2600000}
    captures[914000000] = next(c for c in archive if c.center == 914000000 and c.rate == 20000000)
    timing = remote_timing(captures[435000000], output)
    configs = [(435000000, ('1. Key fob', 433.935e6, 45e3, 32768, 'remote')),
               (951990000, ('2. Downlink #85', 952e6, 100e3, 2048, -53)),
               (951990000, ('3. Downlink #87', 952.4e6, 100e3, 2048, -51)),
               (951990000, ('4. Downlink #89', 952.8e6, 100e3, 8192, None)),
               (907990000, ('5. Uplink #91', 908.2e6, 100e3, 1024, -40))]
    rows, traces = zip(*(measure(captures[center], cfg, timing) for center, cfg in configs))
    signal_figure(rows, traces, output)
    survey_figure(captures, output)
    results = {
        'signals': rows, 'keyfob_timing': timing,
        'gsm_reference': gsm_frequency_reference(captures[951990000]),
        'quiet_span': quiet_span(captures[967990000]),
        'archive': [{'file': c.path.name, 'bytes': c.count * 8, 'samples': c.count,
                     'seconds': c.count / c.rate} for c in archive],
    }
    (output / 'lab01_results.json').write_text(json.dumps(results, indent=2) + '\n', encoding='utf-8')
    print(f'Wrote {len(rows)} signal measurements, {len(archive)} file records and three plots to {output}')


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--data', type=Path, default=ROOT, help='directory containing the archived captures')
    cli.add_argument('--output', type=Path, default=ROOT / 'images', help='directory for plots and JSON results')
    options = cli.parse_args()
    analyze(options.data, options.output)
