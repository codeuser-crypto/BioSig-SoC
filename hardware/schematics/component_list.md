# Component List (Bill of Materials)

Mixed-signal ECG analog front-end. All gain/CMRR/noise targets are justified in
`docs/theory/`. Total system gain ~5000x (500x INA x 10x second stage).

## Instrumentation amplifier stage

| Ref | Part | Source | Value / spec | Justification |
|-----|------|--------|--------------|---------------|
| U1 | INA128P / AD8221ARZ | TI / ADI | CMRR > 90 dB | Single-chip precision INA option |
| U1A,U1B | OPA2134PA | TI | 8 nV/&radic;Hz, low offset | Discrete 3-op-amp INA input buffers |
| U1C | OPA134PA | TI | output diff amp | Difference stage of discrete INA |
| RG | 100 &Omega; 0.1% | - | gain = 1 + 50k/RG = 501x | Sets differential gain |
| R1-R4 | 10 k&Omega; 0.1% matched | - | diff-amp resistors | Matching sets DC CMRR |

## Right-leg drive (RLD)

| Ref | Part | Value | Purpose |
|-----|------|-------|---------|
| U2 | OPA134 / TL071 | - | drives inverted common-mode back to body |
| R5,R6 | 20 k&Omega; | summing | average the two inputs -> common mode |
| R7 | 1 M&Omega; | feedback | RLD loop gain ~50 |
| R8 | 5.1 k&Omega; series | - | patient-protection current limit |
| D1,D2 | 1N4148 | - | input clamp (IEC 60601) |

## High-pass filter (DC offset removal)

| Ref | Part | Value | Note |
|-----|------|-------|------|
| U3A | OPA2134 (1/2) | - | active HP buffer |
| C1 | 3.3 &micro;F film | non-polarized | with R9 sets fc |
| R9 | 1 M&Omega; | - | fc = 1/(2&pi;&middot;1M&middot;3.3&micro;) = 0.048 Hz |
| R10 | 1 M&Omega; | - | bias balance |

## Low-pass anti-aliasing (2nd-order Sallen-Key Butterworth, 150 Hz)

| Ref | Part | Value | Note |
|-----|------|-------|------|
| U3B | OPA2134 (2/2) | - | active LP |
| R11,R12 | 10.7 k&Omega; 1% | - | Butterworth pole placement |
| C2 | 100 nF 1% | - | fc = 1/(2&pi;&radic;(R11 R12 C2 C3)) = 150 Hz |
| C3 | 47 nF 1% | - | Q = 0.707 |

## Second gain stage + offset trim

| Ref | Part | Value | Note |
|-----|------|-------|------|
| U4 | OPA134 | - | non-inverting gain |
| R13 | 10 k&Omega; | - | gain = 1 + R14/R13 = 10x |
| R14 | 90 k&Omega; | - | - |
| R15 | 10 k&Omega; pot | - | DC offset trim (&plusmn;50 mV) |
| Vref | REF02 (5.0 V) | TI | precision mid-rail reference (2.5 V) |

## Power supply

- Dual &plusmn;5 V from a 9 V battery via LT1054 charge pump, or two 9 V cells.
- LM7805 / LM7905 regulators with 10 &micro;F + 100 nF decoupling per op-amp.
- Ferrite bead on each analog supply entry.

## Signal-conditioning output

- R_out: 1 k&Omega; series protects the ADC input from capacitive load.
- Vout -> STM32 PA0 (ADC1 CH0); 2.5 V mid-rail centers signal in 0-3.3 V range.
- STM32 VREF+ from REF3030 (3.0 V) for a stable, low-noise ADC reference.
