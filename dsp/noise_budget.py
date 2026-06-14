"""
noise_budget.py - Complete input-referred noise budget for the ECG front-end.

All noise sources are referred to the INA input (before the 5000x gain) so they
can be compared directly against the AHA ECG noise standard (< 30 uVpp).

Outputs:
  - Console table of each contributor + RSS total + SNR.
  - dsp/noise_plots/noise_budget.png : bar chart of each contributor's share.
"""

from __future__ import annotations

import math
import os

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    _HAVE_MPL = True
except Exception:  # pragma: no cover
    _HAVE_MPL = False

K_BOLTZMANN = 1.380649e-23  # J/K
T_BODY = 310.0  # K (37 C)
BW = 150.0  # Hz (analog noise bandwidth set by anti-alias filter)

# Front-end parameters
R_ELECTRODE = 10e3  # ohm (skin-electrode contact + body)
RG = 100.0  # ohm (INA gain-set resistor)
EN_INA = 8e-9  # V/sqrt(Hz) voltage noise (OPA2134)
IN_INA = 5e-15  # A/sqrt(Hz) current noise
GAIN = 5000.0  # total system gain
VREF = 3.3  # V ADC full scale
ADC_BITS = 12

ECG_SIGNAL = 1e-3  # V (typical R-wave amplitude)

HERE = os.path.dirname(os.path.abspath(__file__))
PLOT_DIR = os.path.join(HERE, "noise_plots")


def thermal_noise(r: float, bw: float = BW, t: float = T_BODY) -> float:
    """Johnson-Nyquist thermal noise voltage (Vrms)."""
    return math.sqrt(4.0 * K_BOLTZMANN * t * r * bw)


def compute_budget() -> dict[str, float]:
    sources = {}
    sources["electrode_thermal"] = thermal_noise(R_ELECTRODE)
    sources["ina_voltage_noise"] = EN_INA * math.sqrt(BW)
    sources["ina_current_noise"] = IN_INA * R_ELECTRODE * math.sqrt(BW)
    sources["resistor_thermal_rg"] = thermal_noise(RG)
    # ADC quantization referred to input: q/sqrt(12) / gain
    lsb = VREF / (2 ** ADC_BITS)
    adc_quant_out = lsb / math.sqrt(12.0)
    sources["adc_quantization"] = adc_quant_out / GAIN
    return sources


def rss(values) -> float:
    return math.sqrt(sum(v * v for v in values))


def main():
    sources = compute_budget()
    total = rss(sources.values())
    snr_db = 20.0 * math.log10(ECG_SIGNAL / total)

    # AHA standard: noise < 30 uVpp == 30 / (2*sqrt(2)) uVrms
    aha_limit_rms = 30e-6 / (2 * math.sqrt(2))

    print("=" * 60)
    print("INPUT-REFERRED NOISE BUDGET (bandwidth = %.0f Hz)" % BW)
    print("=" * 60)
    print(f"{'Source':<24}{'nVrms':>12}{'% of total':>14}")
    print("-" * 60)
    for name, v in sorted(sources.items(), key=lambda kv: -kv[1]):
        pct = 100.0 * (v * v) / (total * total)
        print(f"{name:<24}{v * 1e9:>12.2f}{pct:>13.1f}%")
    print("-" * 60)
    print(f"{'TOTAL (RSS)':<24}{total * 1e9:>12.2f}")
    print()
    print(f"ECG signal (R-wave)      : {ECG_SIGNAL * 1e3:.2f} mV")
    print(f"Input-referred noise     : {total * 1e6:.3f} uVrms")
    print(f"SNR                      : {snr_db:.1f} dB")
    print(f"AHA limit (30 uVpp)      : {aha_limit_rms * 1e6:.2f} uVrms")
    status = "PASS" if total < aha_limit_rms else "FAIL"
    print(f"AHA compliance           : {status} "
          f"({aha_limit_rms / total:.0f}x margin)")

    if _HAVE_MPL:
        os.makedirs(PLOT_DIR, exist_ok=True)
        names = list(sources.keys())
        vals = [sources[n] * 1e9 for n in names]
        plt.figure(figsize=(9, 5))
        bars = plt.bar(names, vals, color="#22d3ee")
        plt.axhline(total * 1e9, color="#f59e0b", linestyle="--",
                    label=f"RSS total {total * 1e9:.1f} nVrms")
        plt.ylabel("Input-referred noise (nVrms)")
        plt.title("ECG Front-End Noise Budget")
        plt.xticks(rotation=20, ha="right")
        plt.legend()
        plt.grid(True, axis="y", alpha=0.3)
        plt.tight_layout()
        out = os.path.join(PLOT_DIR, "noise_budget.png")
        plt.savefig(out, dpi=110)
        plt.close()
        print(f"\nBar chart saved -> {out}")


if __name__ == "__main__":
    main()
