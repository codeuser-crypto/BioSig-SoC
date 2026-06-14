# Filter Response: Measured vs Designed

## Procedure
1. Sweep a sine 0.1-200 Hz at constant amplitude into the input.
2. Measure output amplitude at each frequency (system ADC capture or scope).
3. Plot magnitude (dB) vs frequency; overlay the designed response.

## Designed targets (digital chain, fs = 500 Hz)

| Frequency | Designed | Verified (Q15) |
|-----------|----------|----------------|
| 0.5 Hz | -3 dB (HP edge of FIR band) | from `verify_filters.py` |
| 10 Hz | ~0 dB (passband) | ~0.0 dB PASS |
| 40 Hz | -3 dB (LP edge) | - |
| 50 Hz | notch (deep null) | ~174 dB attenuation* |
| 60 Hz | notch (deep null) | ~117 dB attenuation* |
| 100 Hz | > 60 dB attenuation | ~62 dB PASS |

\*Cascaded ideal-coefficient nulls; on hardware, finite arithmetic and signal
conditioning give practical 40-60 dB rejection.

Run `python dsp/verify_filters.py` to regenerate these from the actual
`filters.h` the firmware uses. Designed plots are in `dsp/filter_plots/`.

## Acceptance criteria
- Passband ripple (0.5-40 Hz): < 0.5 dB
- 60 Hz notch: > 40 dB
- Stopband (> 100 Hz): > 60 dB
- Linear phase (FIR symmetric after Q15): PASS

## Result template

| Frequency | Designed (dB) | Measured (dB) | Delta |
|-----------|---------------|---------------|-------|
| 0.5 | -3 | ___ | ___ |
| 10 | 0 | ___ | ___ |
| 40 | -3 | ___ | ___ |
| 60 | < -40 | ___ | ___ |
| 100 | < -60 | ___ | ___ |
