"""
full_chain_sim.py - End-to-end analog signal-chain simulation (numpy/scipy).

Simulates electrode -> INA -> HP filter -> LP anti-alias -> 2nd gain stage ->
12-bit ADC, with realistic ECG plus common-mode powerline, motion artifact and
electrode DC offset, and shows CMRR rejection of the common-mode interference.

Generates a multi-panel PNG comparing the noisy input against the clean
digitized output, plus before/after noise spectra.
"""

from __future__ import annotations

import os

import numpy as np
import scipy.signal as sig

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    _HAVE_MPL = True
except Exception:  # pragma: no cover
    _HAVE_MPL = False

HERE = os.path.dirname(os.path.abspath(__file__))
PLOT_DIR = os.path.join(HERE, "sim_plots")

FS_ANALOG = 10000.0  # analog simulation rate (Hz)
FS_ADC = 500.0       # ADC sample rate (Hz)
INA_GAIN = 500.0
STAGE2_GAIN = 10.0
CMRR_DB = 80.0
VREF = 3.3
ADC_BITS = 12
MID_RAIL = VREF / 2.0


def generate_ecg(fs=FS_ANALOG, duration=5.0, heart_rate=75.0):
    """Realistic PQRST waveform (mV) built from Gaussian components."""
    n = int(fs * duration)
    t = np.arange(n) / fs
    ecg = np.zeros(n)
    rr = 60.0 / heart_rate
    beats = np.arange(0.4, duration, rr)

    def g(center, amp, width):
        return amp * np.exp(-0.5 * ((t - center) / width) ** 2)

    for bt in beats:
        ecg += g(bt - 0.16, 0.10, 0.020)   # P  wave
        ecg += g(bt - 0.04, -0.05, 0.010)  # Q
        ecg += g(bt, 1.50, 0.008)          # R  (dominant)
        ecg += g(bt + 0.04, -0.15, 0.012)  # S
        ecg += g(bt + 0.20, 0.30, 0.050)   # T  wave

    # Respiratory baseline wander
    ecg += 0.05 * np.sin(2 * np.pi * 0.15 * t)
    return t, ecg * 1e-3  # convert mV -> V


def add_common_mode(t):
    """Common-mode interference present on both electrodes (V)."""
    powerline = 2e-3 * np.sin(2 * np.pi * 60.0 * t)        # 2 mV 60 Hz
    motion = 0.5 * np.sin(2 * np.pi * 1.5 * t + 0.3)       # 500 mV slow drift
    return powerline + motion


def apply_ina(diff_signal, common_mode, gain=INA_GAIN, cmrr_db=CMRR_DB):
    """Differential gain plus leaked common-mode (limited by CMRR)."""
    cm_gain = gain / (10 ** (cmrr_db / 20.0))
    return gain * diff_signal + cm_gain * common_mode


def biquad_hp(x, fc, fs):
    b, a = sig.butter(1, fc / (fs / 2.0), btype="high")
    return sig.lfilter(b, a, x)


def sallen_key_lp(x, fc, fs):
    b, a = sig.butter(2, fc / (fs / 2.0), btype="low")
    return sig.lfilter(b, a, x)


def adc_quantize(x_analog, fs_analog, fs_adc=FS_ADC):
    """Decimate to ADC rate, bias to mid-rail, quantize to 12-bit counts."""
    decim = int(fs_analog / fs_adc)
    x = x_analog[::decim]
    biased = x + MID_RAIL
    biased = np.clip(biased, 0, VREF)
    lsb = VREF / (2 ** ADC_BITS)
    counts = np.round(biased / lsb).astype(int)
    counts = np.clip(counts, 0, 2 ** ADC_BITS - 1)
    return counts, counts * lsb - MID_RAIL


def main():
    t, ecg = generate_ecg()
    cm = add_common_mode(t)
    dc_offset = 0.2  # +200 mV electrode DC offset

    # Two electrode signals = differential ECG + shared CM + DC offset.
    v_plus = ecg / 2 + cm + dc_offset
    v_minus = -ecg / 2 + cm + dc_offset
    diff = v_plus - v_minus  # == ecg

    # INA
    ina_out = apply_ina(diff, cm)

    # HP filter 0.05 Hz removes DC offset / wander, LP 150 Hz anti-aliases.
    hp = biquad_hp(ina_out, 0.05, FS_ANALOG)
    lp = sallen_key_lp(hp, 150.0, FS_ANALOG)

    # 2nd gain stage
    stage2 = lp * STAGE2_GAIN

    # Scale into the ADC window: total gain 5000 puts ECG within +/-1.65 V.
    counts, recovered = adc_quantize(stage2 / (INA_GAIN * STAGE2_GAIN) *
                                     (INA_GAIN * STAGE2_GAIN) * 1.0, FS_ANALOG)

    print("Full-chain simulation complete.")
    print(f"  Analog samples : {len(t)}  ({FS_ANALOG:.0f} Hz)")
    print(f"  ADC samples    : {len(counts)} ({FS_ADC:.0f} Hz)")
    print(f"  INA out p2p     : {np.ptp(ina_out):.3f} V")
    print(f"  ADC count range : {counts.min()} .. {counts.max()}")

    if not _HAVE_MPL:
        print("matplotlib unavailable - skipping plots")
        return

    os.makedirs(PLOT_DIR, exist_ok=True)
    t_adc = np.arange(len(recovered)) / FS_ADC

    fig, ax = plt.subplots(5, 1, figsize=(11, 13))
    ax[0].plot(t, v_plus * 1e3, label="V+", color="#ef4444", linewidth=0.6)
    ax[0].plot(t, v_minus * 1e3, label="V-", color="#3b82f6", linewidth=0.6)
    ax[0].set_title("1. Raw electrode signals (DC offset + common-mode noise)")
    ax[0].set_ylabel("mV")
    ax[0].legend(loc="upper right")

    ax[1].plot(t, ina_out, color="#f59e0b", linewidth=0.6)
    ax[1].set_title("2. After INA (differential amplified, CM rejected)")
    ax[1].set_ylabel("V")

    ax[2].plot(t, hp, color="#10b981", linewidth=0.6)
    ax[2].set_title("3. After HP filter 0.05 Hz (DC offset removed)")
    ax[2].set_ylabel("V")

    ax[3].plot(t, lp, color="#8b5cf6", linewidth=0.6)
    ax[3].set_title("4. After LP anti-alias 150 Hz")
    ax[3].set_ylabel("V")

    ax[4].step(t_adc, recovered, color="#22d3ee", where="mid", linewidth=0.8)
    ax[4].set_title("5. After 12-bit ADC @ 500 Hz (digitized ECG)")
    ax[4].set_ylabel("V")
    ax[4].set_xlabel("Time (s)")

    for a in ax:
        a.grid(True, alpha=0.3)
    fig.tight_layout()
    out = os.path.join(PLOT_DIR, "full_chain.png")
    fig.savefig(out, dpi=110)
    plt.close(fig)

    # Spectrum: input (with CM noise) vs INA output.
    def spec(x, fs):
        xw = (x - np.mean(x)) * np.hanning(len(x))
        mag = np.abs(np.fft.rfft(xw))
        fr = np.fft.rfftfreq(len(x), 1 / fs)
        return fr, 20 * np.log10(mag + 1e-9)

    fr1, s1 = spec(v_plus, FS_ANALOG)
    fr2, s2 = spec(ina_out, FS_ANALOG)
    plt.figure(figsize=(10, 5))
    plt.plot(fr1, s1, label="electrode input", color="#ef4444", linewidth=0.7)
    plt.plot(fr2, s2, label="after INA", color="#22d3ee", linewidth=0.7)
    plt.xlim(0, 200)
    plt.axvline(60, color="gray", linestyle="--", alpha=0.5)
    plt.title("Noise spectrum: before vs after INA (60 Hz CM rejection)")
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Magnitude (dB)")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(PLOT_DIR, "noise_spectrum.png"), dpi=110)
    plt.close()
    print(f"  Plots -> {PLOT_DIR}")


if __name__ == "__main__":
    main()
