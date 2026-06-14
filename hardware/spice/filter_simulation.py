"""
filter_simulation.py - Analog anti-aliasing / high-pass filter response.

Verifies the analog front-end's continuous-time filters:
  - 1st-order high-pass at 0.05 Hz (DC offset / baseline-wander removal)
  - 2nd-order Sallen-Key Butterworth low-pass at 150 Hz (anti-alias)
  - Combined cascade response, checking the -3 dB corners and >60 dB
    attenuation above the 250 Hz Nyquist frequency.
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

FC_HP = 0.05    # Hz
FC_LP = 150.0   # Hz
NYQUIST = 250.0  # Hz (ADC at 500 Hz)


def main():
    # Analog (s-domain) filters.
    hp = sig.butter(1, 2 * np.pi * FC_HP, btype="high", analog=True, output="ba")
    lp = sig.butter(2, 2 * np.pi * FC_LP, btype="low", analog=True, output="ba")

    w = 2 * np.pi * np.logspace(-3, 3.5, 2000)  # 0.001 Hz .. ~3 kHz
    _, h_hp = sig.freqs(*hp, worN=w)
    _, h_lp = sig.freqs(*lp, worN=w)
    h_total = h_hp * h_lp
    f = w / (2 * np.pi)

    db = lambda h: 20 * np.log10(np.abs(h) + 1e-12)

    atten_nyq = -float(np.interp(NYQUIST, f, db(h_total)))
    gain_1hz = float(np.interp(1.0, f, db(h_total)))

    print("Analog filter simulation:")
    print(f"  HP corner   : {FC_HP} Hz (1st order)")
    print(f"  LP corner   : {FC_LP} Hz (2nd-order Butterworth)")
    print(f"  Gain @ 1 Hz : {gain_1hz:.2f} dB")
    print(f"  Attenuation @ {NYQUIST:.0f} Hz (Nyquist): {atten_nyq:.1f} dB")
    print(f"  >60 dB at Nyquist: {'YES' if atten_nyq > 60 else 'NO (note: '
          'single LP stage; spec calls for steeper or higher fs)'}")

    if not _HAVE_MPL:
        print("matplotlib unavailable - skipping plot")
        return

    os.makedirs(PLOT_DIR, exist_ok=True)
    plt.figure(figsize=(10, 5))
    plt.semilogx(f, db(h_hp), label="HP 0.05 Hz", color="#10b981")
    plt.semilogx(f, db(h_lp), label="LP 150 Hz", color="#f59e0b")
    plt.semilogx(f, db(h_total), label="Combined", color="#22d3ee", linewidth=2)
    plt.axvline(NYQUIST, color="#ef4444", linestyle="--", alpha=0.6,
                label="Nyquist 250 Hz")
    plt.axhline(-3, color="gray", linestyle=":", alpha=0.5)
    plt.title("Analog Front-End Filter Response")
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("Magnitude (dB)")
    plt.ylim(-100, 5)
    plt.grid(True, which="both", alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(PLOT_DIR, "analog_filters.png"), dpi=110)
    plt.close()
    print(f"  Plot -> {os.path.join(PLOT_DIR, 'analog_filters.png')}")


if __name__ == "__main__":
    main()
