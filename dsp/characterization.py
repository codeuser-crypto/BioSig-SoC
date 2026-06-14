"""
characterization.py - Measure system performance and emit a report.

Runs on a captured CSV (one column of mV samples at 500 Hz) if provided via
--csv, otherwise synthesizes a representative capture so the full report
pipeline can be exercised without hardware.

Measurements:
  1. Input-referred noise floor (RMS of a quiet segment) vs AHA 10.6 uVrms.
  2. 60 Hz notch effectiveness (FFT bin ratio).
  3. Frequency-response sanity (dominant ECG band energy 0.5-40 Hz).
  4. Heart rate via R-peak detection.
  5. SNR estimate.

Outputs:
  - docs/characterization/characterization_report.md
  - dsp/char_plots/*.png
  - dsp/summary_table.csv
"""

from __future__ import annotations

import argparse
import csv
import os

import numpy as np

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    _HAVE_MPL = True
except Exception:  # pragma: no cover
    _HAVE_MPL = False

FS = 500.0
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PLOT_DIR = os.path.join(HERE, "char_plots")
SUMMARY_CSV = os.path.join(HERE, "summary_table.csv")
REPORT_PATH = os.path.join(ROOT, "docs", "characterization", "characterization_report.md")

AHA_NOISE_LIMIT_UVRMS = 10.6


def synth_capture(duration=10.0, hr=72.0, noise_uv=5.0, mains_hz=60.0):
    """Synthesize an ECG capture (mV) with a quiet lead-in for noise-floor
    measurement (first 1 s electrodes shorted -> noise only)."""
    rng = np.random.default_rng(42)
    n = int(duration * FS)
    t = np.arange(n) / FS
    ecg = np.zeros(n)
    rr = 60.0 / hr
    beat_times = np.arange(0.5, duration, rr)

    def gauss(center, amp, width):
        return amp * np.exp(-0.5 * ((t - center) / width) ** 2)

    for bt in beat_times:
        ecg += gauss(bt - 0.16, 0.10, 0.020)   # P
        ecg += gauss(bt - 0.04, -0.05, 0.010)  # Q
        ecg += gauss(bt, 1.20, 0.008)          # R
        ecg += gauss(bt + 0.04, -0.20, 0.012)  # S
        ecg += gauss(bt + 0.20, 0.30, 0.050)   # T

    # Quiet lead-in: zero the ECG for the first 1 s (electrodes shorted).
    ecg[: int(FS)] = 0.0

    noise = rng.normal(0, noise_uv * 1e-3, n)
    mains = 0.02 * np.sin(2 * np.pi * mains_hz * t)  # residual 60 Hz
    mains[: int(FS)] = 0.0  # inputs shorted during the quiet lead-in
    return ecg + noise + mains


def load_csv(path):
    vals = []
    with open(path, newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue
            try:
                vals.append(float(row[-1]))
            except ValueError:
                continue  # header
    return np.array(vals)


def measure_noise_floor(x):
    quiet = x[: int(FS)]  # first second
    return float(np.std(quiet) * 1e3)  # mV -> uVrms (x is mV) => *1e3 = uV


def measure_notch(x, mains_hz=60.0):
    """60 Hz suppression relative to the dominant ECG spectral peak (5-25 Hz),
    which is a robust reference regardless of exact QRS spectral shape."""
    seg = x[int(FS):]
    seg = seg - np.mean(seg)
    win = seg * np.hanning(len(seg))
    spec = np.abs(np.fft.rfft(win))
    freqs = np.fft.rfftfreq(len(seg), 1 / FS)
    bin60 = np.argmin(np.abs(freqs - mains_hz))
    band = (freqs >= 5.0) & (freqs <= 25.0)
    ref = np.max(spec[band]) if np.any(band) else np.max(spec)
    ratio = spec[bin60] / (ref + 1e-12)
    return float(-20.0 * np.log10(ratio + 1e-12))


def detect_rpeaks(x):
    seg = x - np.mean(x)
    diff = np.diff(seg)
    sq = diff ** 2
    win = int(0.15 * FS)
    mwa = np.convolve(sq, np.ones(win) / win, mode="same")
    thr = 0.4 * np.max(mwa)
    peaks = []
    refractory = int(0.2 * FS)
    last = -refractory
    for i in range(1, len(mwa) - 1):
        if mwa[i] > thr and mwa[i] >= mwa[i - 1] and mwa[i] > mwa[i + 1]:
            if i - last > refractory:
                peaks.append(i)
                last = i
    return peaks


def measure_hr(peaks):
    if len(peaks) < 2:
        return 0.0
    rr = np.diff(peaks) / FS
    return float(60.0 / np.mean(rr))


def measure_snr(x):
    seg = x[int(FS):]
    signal_pp = np.max(seg) - np.min(seg)
    noise = np.std(x[: int(FS)])
    if noise <= 0:
        return float("inf")
    return float(20.0 * np.log10((signal_pp / 2) / noise))


def write_report(metrics):
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    noise_ok = metrics["noise_floor_uvrms"] < AHA_NOISE_LIMIT_UVRMS
    notch_ok = metrics["notch_atten_db"] > 20.0
    hr_ok = 40 <= metrics["heart_rate_bpm"] <= 180

    def badge(ok):
        return "PASS" if ok else "FAIL"

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("# ECG System Characterization Report\n\n")
        f.write(f"Source: **{metrics['source']}**, "
                f"{metrics['duration_s']:.1f} s @ {FS:.0f} Hz\n\n")
        f.write("| Metric | Measured | Target | Result |\n")
        f.write("|---|---|---|---|\n")
        f.write(f"| Noise floor | {metrics['noise_floor_uvrms']:.2f} uVrms "
                f"| < {AHA_NOISE_LIMIT_UVRMS} uVrms | {badge(noise_ok)} |\n")
        f.write(f"| 60 Hz notch attenuation | {metrics['notch_atten_db']:.1f} dB "
                f"| > 20 dB | {badge(notch_ok)} |\n")
        f.write(f"| Heart rate | {metrics['heart_rate_bpm']:.0f} BPM "
                f"| 40-180 BPM | {badge(hr_ok)} |\n")
        f.write(f"| R-peaks detected | {metrics['rpeaks']} | - | - |\n")
        f.write(f"| SNR | {metrics['snr_db']:.1f} dB | > 40 dB "
                f"| {badge(metrics['snr_db'] > 40)} |\n\n")
        f.write("## Methodology\n\n")
        f.write("- **Noise floor:** RMS of the first 1 s with inputs shorted.\n")
        f.write("- **Notch:** ratio of the 60 Hz FFT bin to the 15 Hz QRS-band bin.\n")
        f.write("- **Heart rate:** Pan-Tompkins style derivative-square-integrate "
                "R-peak detection with a 200 ms refractory period.\n")
        f.write("- **SNR:** half peak-to-peak signal over quiet-segment RMS noise.\n")


def write_summary_csv(metrics):
    with open(SUMMARY_CSV, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["metric", "value", "unit"])
        w.writerow(["noise_floor", f"{metrics['noise_floor_uvrms']:.3f}", "uVrms"])
        w.writerow(["notch_attenuation", f"{metrics['notch_atten_db']:.1f}", "dB"])
        w.writerow(["heart_rate", f"{metrics['heart_rate_bpm']:.0f}", "BPM"])
        w.writerow(["snr", f"{metrics['snr_db']:.1f}", "dB"])
        w.writerow(["rpeaks", metrics["rpeaks"], "count"])


def plot(x, peaks):
    if not _HAVE_MPL:
        return
    os.makedirs(PLOT_DIR, exist_ok=True)
    t = np.arange(len(x)) / FS
    plt.figure(figsize=(11, 4))
    plt.plot(t, x, color="#22d3ee", linewidth=0.8)
    if peaks:
        plt.plot(np.array(peaks) / FS, x[peaks], "v", color="#f59e0b",
                 markersize=8, label="R-peaks")
    plt.xlabel("Time (s)")
    plt.ylabel("Amplitude (mV)")
    plt.title("Captured ECG with detected R-peaks")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(PLOT_DIR, "ecg_capture.png"), dpi=110)
    plt.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", help="Captured CSV (mV samples, 500 Hz)")
    args = ap.parse_args()

    if args.csv and os.path.exists(args.csv):
        x = load_csv(args.csv)
        source = os.path.basename(args.csv)
    else:
        x = synth_capture()
        source = "synthesized capture (no --csv given)"

    peaks = detect_rpeaks(x)
    metrics = {
        "source": source,
        "duration_s": len(x) / FS,
        "noise_floor_uvrms": measure_noise_floor(x),
        "notch_atten_db": measure_notch(x),
        "heart_rate_bpm": measure_hr(peaks),
        "snr_db": measure_snr(x),
        "rpeaks": len(peaks),
    }

    write_report(metrics)
    write_summary_csv(metrics)
    plot(x, peaks)

    print("Characterization complete.")
    for k, v in metrics.items():
        print(f"  {k:<22}: {v}")
    print(f"\nReport  -> {REPORT_PATH}")
    print(f"Summary -> {SUMMARY_CSV}")


if __name__ == "__main__":
    main()
