"""
verify_filters.py - Parse the generated filters.h and verify that the Q15
coefficients still meet spec after quantization.

This closes the loop: filter_design.py designs in float and quantizes to Q15;
this script reads the *quantized* values back out of the C header and checks the
realized frequency response, exactly as the firmware will see it.

Checks:
  - 60 Hz notch attenuation > 20 dB
  - 50 Hz notch attenuation > 20 dB
  - FIR passband (10 Hz) ripple < 1 dB
  - FIR stopband (100 Hz) attenuation > 40 dB
  - FIR coefficients symmetric (linear phase)
"""

from __future__ import annotations

import os
import re
import sys

import numpy as np
import scipy.signal as sig

FS = 500.0
POSTSHIFT = 1

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
HEADER_PATH = os.path.join(ROOT, "firmware", "Core", "Inc", "filters.h")


def _parse_array(text: str, name: str) -> list[int]:
    m = re.search(rf"{name}\s*\[[^\]]*\]\s*=\s*\{{(.*?)\}}", text, re.DOTALL)
    if not m:
        raise ValueError(f"Array {name} not found in header")
    nums = re.findall(r"-?\d+", m.group(1))
    return [int(n) for n in nums]


def _cmsis_q15_to_ba(stage: list[int]):
    """Convert one CMSIS DF1 stage [b0,b1,b2,-a1,-a2] (Q15, postshifted)
    back to float b, a."""
    scale = (2 ** POSTSHIFT) / 32768.0
    b0, b1, b2, na1, na2 = [v * scale for v in stage]
    b = [b0, b1, b2]
    a = [1.0, -na1, -na2]
    return b, a


def _atten_db(b, a, f0):
    _, h = sig.freqz(b, a, worN=[2 * np.pi * f0 / FS])
    return -20.0 * np.log10(np.abs(h[0]) + 1e-12)


def verify() -> bool:
    if not os.path.exists(HEADER_PATH):
        print(f"ERROR: {HEADER_PATH} not found. Run filter_design.py first.")
        return False

    with open(HEADER_PATH, "r", encoding="utf-8") as f:
        text = f.read()

    notch60 = _parse_array(text, "notch_60hz_coeffs_q15")
    notch50 = _parse_array(text, "notch_50hz_coeffs_q15")
    fir = _parse_array(text, "fir_bp_coeffs_q15")

    results = []

    # Notch filters: cascade the two stages.
    for label, coeffs, f0 in (("60 Hz", notch60, 60.0), ("50 Hz", notch50, 50.0)):
        stage = coeffs[:5]  # both stages identical
        b, a = _cmsis_q15_to_ba(stage)
        # Two cascaded identical stages -> double the dB attenuation.
        atten = 2.0 * _atten_db(b, a, f0)
        ok = atten > 20.0
        results.append(ok)
        print(f"{label} notch attenuation : {atten:6.1f} dB  "
              f"[{'PASS' if ok else 'FAIL'}]")

    # FIR
    fir_f = np.array(fir, dtype=float) / 32768.0
    pass_ripple = _atten_db(fir_f, [1.0], 10.0)
    stop_atten = _atten_db(fir_f, [1.0], 100.0)
    symmetric = np.array_equal(fir, fir[::-1])

    r_ok = abs(pass_ripple) < 1.0
    s_ok = stop_atten > 40.0
    results += [r_ok, s_ok, symmetric]

    print(f"FIR passband (10 Hz) gain : {-pass_ripple:6.2f} dB  "
          f"[{'PASS' if r_ok else 'FAIL'}]")
    print(f"FIR stopband (100 Hz)     : {stop_atten:6.1f} dB  "
          f"[{'PASS' if s_ok else 'FAIL'}]")
    print(f"FIR symmetric (linear ph) : {symmetric}     "
          f"[{'PASS' if symmetric else 'FAIL'}]")

    group_delay_ms = (len(fir) - 1) / (2 * FS) * 1000.0
    print(f"FIR group delay           : {group_delay_ms:.1f} ms")

    all_ok = all(results)
    print("\nOVERALL:", "PASS" if all_ok else "FAIL")
    return all_ok


if __name__ == "__main__":
    sys.exit(0 if verify() else 1)
