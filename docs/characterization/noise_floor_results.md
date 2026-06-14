# Noise Floor Measurement

## Procedure
1. Short the electrode inputs (or use a 10 k&Omega; balanced dummy source).
2. Capture >= 10 s at 500 sps (`wireless/uart_receiver.py --log`).
3. Band-limit to 0.5-40 Hz (the DSP already does this) and compute RMS.
4. Refer to input: divide output RMS by the total gain (5000).

## Expected / target

| Quantity | Value |
|----------|-------|
| Input-referred noise (predicted) | ~0.19 &micro;Vrms |
| AHA limit (30 &micro;Vpp) | 10.6 &micro;Vrms |
| Margin | ~55x |
| SNR (1 mV R-wave) | ~74 dB |

Predicted budget: `python dsp/noise_budget.py`.
Measured from a capture: `python dsp/characterization.py --csv <capture.csv>`.

## Result template (fill from your hardware)

| Metric | Measured | Target | Result |
|--------|----------|--------|--------|
| Noise floor (input-referred) | ___ &micro;Vrms | < 10.6 &micro;Vrms | ___ |
| Noise floor (output) | ___ mVrms | - | - |
| SNR @ 1 mV | ___ dB | > 40 dB | ___ |

## Notes
- Dominant contributor is electrode thermal noise (~68% of the budget), so the
  amplifier is not the limiting element - good design balance.
- Increasing the analog bandwidth raises noise as &radic;BW; the 150 Hz LP keeps
  it in check.
