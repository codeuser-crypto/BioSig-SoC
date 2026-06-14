# Instrumentation Amplifier Design

## Why an INA for ECG?
ECG is a small (0.5-5 mV) **differential** signal riding on a large (up to
volts) **common-mode** interference from 50/60 Hz mains and the body acting as
an antenna. An instrumentation amplifier amplifies the difference while
rejecting the common mode - quantified by CMRR.

## Three-op-amp topology
- **Input stage (U1A/U1B):** two non-inverting buffers sharing one gain
  resistor RG. Differential gain:
  ```
  A_diff = 1 + 2*R_f/RG
  ```
  With the internal 25 k&Omega; feedback resistors and RG = 100 &Omega;,
  A_diff ~ 500. Crucially, the common-mode gain of this stage is **unity**, so
  CM signal is not amplified before the difference stage.
- **Difference stage (U1C):** unity-gain diff amp with four matched resistors
  (R1-R4) converts differential to single-ended.

## CMRR
```
CMRR_dB = 20 * log10(A_diff / A_cm)
A_cm    = A_diff / 10^(CMRR_dB/20)
```
DC CMRR is dominated by the difference-stage resistor matching. For a tolerance
`t`:
```
CMRR ~ A_diff / (4*t)
```
0.1% resistors (t = 0.001) with A_diff = 500 give ~102 dB ideal; real parts and
op-amp finite CMRR bring this to the 80-96 dB range (see
`hardware/spice/ina_simulation.py`). CMRR degrades at higher frequency as the
op-amp open-loop gain rolls off (GBW/f).

## Right-leg drive
Feeding the inverted, amplified common-mode signal back into the body's
reference electrode forms a feedback loop that actively drives the patient's
common-mode voltage toward the amplifier reference, adding 20-40 dB of
effective CMRR at mains frequency.

## Gain budget
- INA: 500x
- Second stage: 10x
- Total: ~5000x -> 5 mV ECG -> 2.5 V swing centered on the 1.65 V ADC mid-rail.
