"""
ina_simulation.py - Instrumentation-amplifier CMRR and noise simulation.

Models the 3-op-amp INA:
  - Differential gain  A_diff = 1 + 2*R/RG  (here configured for ~500x)
  - Common-mode gain limited by resistor mismatch in the diff-amp stage
  - Input-referred voltage noise of the input op-amps

Sweeps CMRR vs frequency (op-amp open-loop gain rolls off, degrading CMRR)
and prints/plots the result.
"""

from __future__ import annotations

import os

import numpy as np

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    _HAVE_MPL = True
except Exception:  # pragma: no cover
    _HAVE_MPL = False

HERE = os.path.dirname(os.path.abspath(__file__))
PLOT_DIR = os.path.join(HERE, "sim_plots")

A_DIFF = 500.0
RESISTOR_MISMATCH = 0.001  # 0.1% matched resistors
GBW = 8e6  # op-amp gain-bandwidth product (Hz), OPA2134-class
EN = 8e-9  # V/sqrt(Hz) input voltage noise


def cmrr_vs_freq(freqs):
    """CMRR(f) in dB. DC CMRR set by resistor matching; degrades with the
    finite, frequency-dependent op-amp open-loop gain."""
    # DC CMRR from 0.1% diff-amp resistor matching: CMRR ~ A_diff / (4*mismatch)
    cmrr_dc = A_DIFF / (4 * RESISTOR_MISMATCH)
    # Open-loop gain magnitude rolls off as GBW/f.
    aol = GBW / np.maximum(freqs, 1.0)
    # Effective CMRR limited by the smaller of matched-resistor and aol terms.
    cmrr = 1.0 / (1.0 / cmrr_dc + 1.0 / aol)
    return 20 * np.log10(cmrr)


def main():
    freqs = np.logspace(0, 3, 200)  # 1 Hz .. 1 kHz
    cmrr_db = cmrr_vs_freq(freqs)

    cmrr_60 = float(np.interp(60.0, freqs, cmrr_db))
    cmrr_50 = float(np.interp(50.0, freqs, cmrr_db))
    noise_rms = EN * np.sqrt(150.0)  # input-referred over 150 Hz BW

    print("INA simulation:")
    print(f"  Differential gain     : {A_DIFF:.0f}x")
    print(f"  CMRR @ 50 Hz          : {cmrr_50:.1f} dB")
    print(f"  CMRR @ 60 Hz          : {cmrr_60:.1f} dB")
    print(f"  Input voltage noise   : {noise_rms * 1e9:.1f} nVrms (150 Hz BW)")

    if not _HAVE_MPL:
        print("matplotlib unavailable - skipping plot")
        return

    os.makedirs(PLOT_DIR, exist_ok=True)
    plt.figure(figsize=(9, 5))
    plt.semilogx(freqs, cmrr_db, color="#22d3ee")
    plt.axvline(60, color="#ef4444", linestyle="--", alpha=0.6, label="60 Hz")
    plt.axvline(50, color="#f59e0b", linestyle="--", alpha=0.6, label="50 Hz")
    plt.axhline(80, color="#10b981", linestyle=":", alpha=0.6, label="80 dB target")
    plt.title("INA CMRR vs Frequency")
    plt.xlabel("Frequency (Hz)")
    plt.ylabel("CMRR (dB)")
    plt.grid(True, which="both", alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(PLOT_DIR, "ina_cmrr.png"), dpi=110)
    plt.close()
    print(f"  Plot -> {os.path.join(PLOT_DIR, 'ina_cmrr.png')}")


if __name__ == "__main__":
    main()
