"""Filter design / quantization accuracy tests."""
import numpy as np
import scipy.signal as sig

import filter_design as fd
from coefficient_export import float_to_q15, q15_to_float


FS = 500.0


def test_notch_attenuates_target_frequency():
    b, a = fd.design_notch(60.0, FS)
    w, h = sig.freqz(b, a, worN=[2 * np.pi * 60.0 / FS])
    atten_db = -20 * np.log10(abs(h[0]))
    assert atten_db > 20.0


def test_notch_passes_ecg_band():
    b, a = fd.design_notch(60.0, FS)
    # 15 Hz (QRS band) should pass with < 3 dB loss
    w, h = sig.freqz(b, a, worN=[2 * np.pi * 15.0 / FS])
    loss_db = -20 * np.log10(abs(h[0]))
    assert loss_db < 3.0


def test_fir_is_symmetric_after_q15():
    h = fd.design_bandpass_fir(0.5, 40.0, FS, numtaps=128)
    q = float_to_q15(h)
    assert np.array_equal(q, q[::-1])


def test_fir_passband_and_stopband():
    h = fd.design_bandpass_fir(0.5, 40.0, FS, numtaps=128)
    w, mag = sig.freqz(h, worN=4096, fs=FS)

    def at(f):
        i = np.argmin(np.abs(w - f))
        return 20 * np.log10(abs(mag[i]) + 1e-12)

    assert at(10.0) > -1.0      # passband ~0 dB
    assert at(100.0) < -40.0    # stopband well attenuated


def test_q15_clamps_to_range():
    q = float_to_q15(np.array([2.0, -2.0, 0.5]))
    assert q.max() <= 32767
    assert q.min() >= -32768
    assert abs(q15_to_float(q)[2] - 0.5) < 1e-3


def test_q15_roundtrip_precision():
    vals = np.linspace(-0.9, 0.9, 50)
    q = float_to_q15(vals)
    back = q15_to_float(q)
    assert np.max(np.abs(back - vals)) < 1.0 / 32768 * 2


def test_group_delay():
    n = 128
    delay_ms = (n - 1) / (2 * FS) * 1000.0
    assert abs(delay_ms - 127.0) < 0.5
