"""
coefficient_export.py - Standalone float -> Q15 conversion helpers.

filter_design.py already writes filters.h directly, but these helpers are kept
separate so tests and other tools can reuse the exact same quantization logic
without triggering plot generation or file writes.
"""

from __future__ import annotations

import numpy as np


def float_to_q15(coeffs) -> np.ndarray:
    """Convert float array to Q15 int16 (clamped to [-1, 1)). """
    arr = np.asarray(coeffs, dtype=float)
    scaled = np.clip(arr, -1.0, 1.0 - 1.0 / 32768.0) * 32768.0
    return np.round(scaled).astype(np.int16)


def q15_to_float(q15) -> np.ndarray:
    """Inverse of float_to_q15 (for verification)."""
    return np.asarray(q15, dtype=float) / 32768.0


def biquad_to_cmsis_q15(b, a, postshift: int = 1) -> list[int]:
    """CMSIS DF1 Q15 [b0, b1, b2, -a1, -a2], pre-scaled by 2^-postshift."""
    scale = 1.0 / (2 ** postshift)
    coeffs = np.array([b[0], b[1], b[2], -a[1], -a[2]]) * scale
    return float_to_q15(coeffs).tolist()


def format_c_array(name: str, values, ctype: str = "q15_t", per_line: int = 8) -> str:
    """Render a values list as a C array definition string."""
    body_lines = []
    vals = list(values)
    for i in range(0, len(vals), per_line):
        chunk = ", ".join(f"{int(v):6d}" for v in vals[i : i + per_line])
        body_lines.append("    " + chunk + ",")
    body = "\n".join(body_lines)
    return f"static const {ctype} {name}[{len(vals)}] = {{\n{body}\n}};\n"


if __name__ == "__main__":
    demo = np.array([0.5, -0.25, 0.999, -1.0])
    q = float_to_q15(demo)
    print("float :", demo)
    print("Q15   :", q)
    print("back  :", q15_to_float(q))
    print(format_c_array("demo_coeffs", q))
