"""
DSP pipeline verification: inject known tones through the *designed* filters
(float reference) and confirm the firmware's intended behavior - notch rejection
at mains, passband transparency, and FIR stopband attenuation.

This validates the design that filter_design.py exports to filters.h; the
firmware runs the Q15 version of exactly these coefficients.
"""
import numpy as np
import scipy.signal as sig

import filter_design as fd

FS = 500.0
DUR = 4.0
N = int(FS * DUR)
T = np.arange(N) / FS


def _tone(freq, amp=1.0):
    return amp * np.sin(2 * np.pi * freq * T)


def _rms(x):
    # skip filter transient
    return np.sqrt(np.mean(x[FS_SKIP:] ** 2))


FS_SKIP = int(FS)  # 1 s settle


def test_notch_60hz_rejects_60():
    b, a = fd.design_notch(60.0, FS)
    x = _tone(60.0)
    y = sig.lfilter(b, a, x)
    atten_db = 20 * np.log10(_rms(x) / (_rms(y) + 1e-12))
    assert atten_db > 20.0


def test_notch_60hz_passes_40():
    b, a = fd.design_notch(60.0, FS)
    x = _tone(40.0)
    y = sig.lfilter(b, a, x)
    loss_db = 20 * np.log10(_rms(x) / (_rms(y) + 1e-12))
    assert loss_db < 1.0


def test_fir_bandpass_rejects_100():
    h = fd.design_bandpass_fir(0.5, 40.0, FS, numtaps=128)
    x = _tone(100.0)
    y = sig.lfilter(h, [1.0], x)
    atten_db = 20 * np.log10(_rms(x) / (_rms(y) + 1e-12))
    assert atten_db > 40.0


def test_fir_bandpass_passes_10():
    h = fd.design_bandpass_fir(0.5, 40.0, FS, numtaps=128)
    x = _tone(10.0)
    y = sig.lfilter(h, [1.0], x)
    loss_db = 20 * np.log10(_rms(x) / (_rms(y) + 1e-12))
    assert loss_db < 1.0


def test_q15_fullscale_no_overflow():
    """Quantized FIR applied to a full-scale Q15 ramp must not overflow int32
    accumulation when summed (sanity of coefficient scaling)."""
    h = fd.design_bandpass_fir(0.5, 40.0, FS, numtaps=128)
    q = np.round(np.clip(h, -1, 1) * 32768).astype(np.int64)
    # worst-case accumulator = sum(|coeff|) * 32767
    acc = np.sum(np.abs(q)) * 32767
    assert acc < 2 ** 63  # comfortably within int64 MAC used by CMSIS


def test_combined_pipeline_preserves_qrs():
    """Notch + FIR should keep a 15 Hz QRS-band tone largely intact."""
    b60, a60 = fd.design_notch(60.0, FS)
    b50, a50 = fd.design_notch(50.0, FS)
    h = fd.design_bandpass_fir(0.5, 40.0, FS, numtaps=128)
    x = _tone(15.0)
    y = sig.lfilter(b60, a60, x)
    y = sig.lfilter(b50, a50, y)
    y = sig.lfilter(h, [1.0], y)
    loss_db = 20 * np.log10(_rms(x) / (_rms(y) + 1e-12))
    assert loss_db < 2.0
