# Noise Analysis

## Johnson-Nyquist thermal noise
A resistor R at temperature T contributes a noise voltage over bandwidth BW:

```
v_n = sqrt(4 * k * T * R * BW)
```
with k = 1.38e-23 J/K. At body temperature (T = 310 K) the electrode-tissue
resistance (R ~ 10 k&Omega;) over the 150 Hz analog bandwidth gives ~160 nVrms.

## Op-amp noise model
Each input op-amp adds a voltage-noise density `en` (V/&radic;Hz) and a
current-noise density `in` (A/&radic;Hz). Referred to the input over bandwidth BW:

```
v_en = en * sqrt(BW)
v_in = in * R_source * sqrt(BW)
```
For the OPA2134 (en = 8 nV/&radic;Hz, in = 5 fA/&radic;Hz): v_en ~ 98 nVrms,
v_in ~ 0.6 nVrms (negligible).

## Input-referred budget (3-op-amp INA)
All sources are referred to the INA input so they compare directly to the
clinical limit. Combined by root-sum-square (RSS):

| Source | nVrms |
|--------|-------|
| Electrode thermal (10 k&Omega;) | ~160 |
| INA voltage noise | ~98 |
| ADC quantization (referred) | ~47 |
| RG thermal (100 &Omega;) | ~16 |
| INA current noise | ~0.6 |
| **RSS total** | **~194** |

(Run `python dsp/noise_budget.py` for the exact numbers + bar chart.)

## Comparison to the AHA ECG standard
The AHA limits ECG noise to **< 30 &micro;Vpp**, i.e. 30/(2&radic;2) ~ 10.6
&micro;Vrms input-referred. Our ~0.19 &micro;Vrms sits ~55x below the limit:

```
SNR (1 mV R-wave) = 20*log10(1e-3 / 194e-9) = 74.2 dB
```

## Measurement methodology
1. Short the electrode inputs together (or use a 10 k&Omega; dummy source).
2. Capture >= 10 s at 500 sps; compute the RMS of the band-limited output.
3. Divide by total gain (5000) to refer back to the input.
4. Compare RMS against 10.6 &micro;Vrms; convert to pp (x2&radic;2) for the AHA
   30 &micro;Vpp spec.
