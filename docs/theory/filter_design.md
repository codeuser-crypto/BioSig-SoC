# Filter Design Methodology

Two domains: continuous-time analog (front-end) and discrete-time digital
(STM32 DSP). The analog filters condition and anti-alias; the digital filters
clean up mains interference and isolate the diagnostic ECG band.

## Analog filters
- **High-pass 0.05 Hz (1st order):** removes electrode DC offset and baseline
  wander. fc chosen below the lowest diagnostic content (~0.05 Hz) to avoid ST
  distortion.
- **Low-pass 150 Hz (2nd-order Sallen-Key Butterworth, Q = 0.707):** anti-alias
  for the 500 Hz ADC. Butterworth chosen for **maximally flat passband** - no
  ripple in the 0.5-40 Hz ECG band means no waveform distortion (vs Chebyshev,
  which trades passband ripple for a steeper skirt).

See `hardware/spice/filter_simulation.py`.

## Digital filters (designed in `dsp/filter_design.py`, fs = 500 Hz)

### 50/60 Hz IIR notch (2nd-order biquad)
```
H(z) = (1 - 2cos(w0) z^-1 + z^-2) / (1 - 2 r cos(w0) z^-1 + r^2 z^-2)
w0 = 2*pi*f0/fs
```
Pole radius `r` (0.985 here) sets the notch bandwidth ~ (1-r)/pi * fs ~ 2.4 Hz.
Two identical stages are cascaded to sharpen the null. Coefficients are exported
in CMSIS DF1 layout `[b0, b1, b2, -a1, -a2]` with a post-shift of 1.

### Bandpass FIR 0.5-40 Hz (128-tap, linear phase)
Window method (`firwin2`, Hamming). Linear phase preserves QRS morphology -
critical for clinical interpretation. Group delay is constant:
```
group_delay = (N-1)/(2*fs) = 127 / 1000 = 127 ms
```
This 127 ms is the dominant latency in the firmware chain (and is compensable
since it is exactly known and constant).

## Fixed-point (Q15)
Float coefficients are scaled by 32768 and rounded to int16, clamped to
&plusmn;32767. FIR symmetry is verified **after** quantization to guarantee the
realized filter is still linear phase. `dsp/verify_filters.py` reads the
generated header back and confirms the quantized response still meets spec.
