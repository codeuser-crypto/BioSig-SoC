# Analog Front-End - Schematic Description & Netlist

Signal flow (left to right):

```
Electrodes --> Protection --> 3-op-amp INA --> HP 0.05Hz --> LP 150Hz --> Gain x10 --> ADC
   |                             ^
   +-------- Right-Leg Drive ----+   (inverted common-mode fed back to body)
```

## Stage-by-stage

### 1. Input protection (IEC 60601)
Each electrode connects through a 5.1 k&Omega; series resistor (R8) and clamp
diodes (D1/D2, 1N4148) to the supply rails, limiting fault current into the
patient and protecting the INA inputs from defibrillation transients/ESD.

### 2. Instrumentation amplifier (gain 500x)
Three-op-amp topology:
- Two non-inverting input buffers (U1A/U1B, OPA2134) share a single gain
  resistor RG = 100 &Omega;, giving differential gain `1 + 2*25k/RG ~ 500`
  (or `1 + 50k/RG` for the integrated INA128 internal network).
- A unity difference amplifier (U1C) with matched 10 k&Omega; resistors
  (R1-R4) converts differential to single-ended and rejects common mode.
- DC CMRR is set by resistor matching: 0.1% match -> ~74 dB; trimming/auto-zero
  pushes it past 90 dB.

### 3. Right-leg drive
R5/R6 (20 k&Omega;) average the two input nodes to extract the common-mode
voltage; U2 inverts and amplifies it (R7 = 1 M&Omega;, gain ~50) and drives it
back into the patient's reference electrode, actively cancelling 50/60 Hz
common-mode pickup and improving effective CMRR by 20-40 dB.

### 4. High-pass filter, fc = 0.05 Hz
Active first-order HP (U3A, C1 = 3.3 &micro;F, R9 = 1 M&Omega;) removes the
&plusmn;200 mV electrode half-cell DC offset and respiratory baseline wander
without distorting the ST segment.

### 5. Low-pass anti-aliasing, fc = 150 Hz
2nd-order Sallen-Key Butterworth (U3B, R11/R12 = 10.7 k&Omega;, C2 = 100 nF,
C3 = 47 nF), Q = 0.707. Maximally flat passband; attenuates content above the
250 Hz Nyquist of the 500 Hz ADC.

### 6. Second gain stage, x10
Non-inverting (U4, R13 = 10 k&Omega;, R14 = 90 k&Omega;). Brings total gain to
~5000 so a 5 mV ECG R-wave reaches ~2.5 V at the ADC input around the 1.65 V
mid-rail bias.

## Netlist (abbreviated SPICE-style)

```
* nodes: EL_P EL_N (electrodes), CM (right-leg), OUT (to ADC), V25 (2.5V ref)
R8a  EL_P  IN_P  5.1k
R8b  EL_N  IN_N  5.1k
D1   IN_P  VDD   D1N4148
D2   VSS   IN_P  D1N4148
XU1  IN_P IN_N RG OUT_INA  INA_3OPAMP   ; gain 500
RG   gain_a gain_b 100
XHP  OUT_INA OUT_HP  HP_0p05            ; C1=3.3u R9=1Meg
XLP  OUT_HP  OUT_LP  SK_LP_150          ; R11=R12=10.7k C2=100n C3=47n
XU4  OUT_LP  OUT     GAIN_10            ; R13=10k R14=90k
ROUT OUT     ADC_IN  1k
VREF V25 0 DC 2.5
```

See `hardware/spice/full_chain_sim.py` for the numeric end-to-end simulation
that exercises this chain with realistic ECG + interference.
