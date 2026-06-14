# CMRR Measurement Procedure & Results

## Test equipment
- Function generator (sine, 1 mVpp-1 Vpp, 1-200 Hz)
- Oscilloscope (>= 12-bit or averaging) or the system's own ADC capture
- Precision multimeter
- 10 k&Omega; 0.1% resistors (source-impedance balance)

## Procedure
1. **Differential gain A_diff:** apply a small differential signal (e.g. 1 mVpp
   at 10 Hz across EL_P/EL_N), measure output amplitude. `A_diff = Vout/Vin`.
2. **Common-mode gain A_cm:** tie EL_P and EL_N together, apply the *same*
   signal to both relative to the reference, measure output. `A_cm = Vout/Vin`.
3. **CMRR:** `CMRR_dB = 20*log10(A_diff / A_cm)`.
4. Repeat at 10, 50, 60, 100, 200 Hz.

## Expected results

| Frequency (Hz) | CMRR (dB) | Notes |
|----------------|-----------|-------|
| 10 | ~96 | matching-limited |
| 50 | ~90-96 | mains (50 Hz regions) |
| 60 | ~88-96 | mains (60 Hz regions) |
| 100 | ~84 | op-amp GBW roll-off begins |
| 200 | ~78 | - |

Simulated curve: `python hardware/spice/ina_simulation.py`.

## Pass/fail (IEC 60601-2-47)
- **Pass:** CMRR > 80 dB at the local mains frequency (with right-leg drive
  active).
- The RLD loop should add 20-40 dB over the bare INA value.

## Troubleshooting
| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Low CMRR at DC | resistor mismatch in diff stage | use 0.1% / trim R |
| CMRR good DC, bad at 60 Hz | source-impedance imbalance | balance electrode leads |
| 60 Hz on output even with RLD | RLD loop not closed / wrong polarity | verify RLD feedback sign |
| CMRR drops above 100 Hz | op-amp GBW limit | expected; use faster op-amp if needed |
