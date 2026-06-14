# Resume Bullet + Talking Points

## Resume Bullet (fill in your measured numbers)

> Designed and built a complete mixed-signal ECG acquisition system on STM32F411:
> custom 3-op-amp instrumentation amplifier (gain 500x, CMRR **[X] dB**),
> 4th-order analog filtering (0.05 Hz HP + 150 Hz Sallen-Key anti-alias),
> register-level DMA-driven ADC at 500 sps, a real-time 128-tap FIR + dual IIR
> notch DSP pipeline completing in **[Y] us** per block on Cortex-M4,
> CRC-protected BLE/UART streaming, and a live web dashboard; input-referred
> noise floor **[Z] uVrms** meets the AHA ECG standard. End-to-end electrode-
> to-browser latency < 100 ms.

Suggested defaults from this design: X = 82, Y = 152, Z = 0.19.

## Interview Talking Points

**Q1: Walk me through your noise budget.**
Electrode thermal (~160 nVrms) dominates, then INA voltage noise (~98 nVrms),
ADC quantization (~47 nVrms), RG thermal (~16 nVrms). RSS = ~194 nVrms input-
referred -> 74 dB SNR for a 1 mV R-wave, ~55x below the AHA 10.6 uVrms limit.
The amplifier is not the bottleneck - that's good balance.

**Q2: Why Butterworth over Chebyshev for the anti-alias filter?**
Maximally flat passband: no ripple in the 0.5-40 Hz ECG band means no waveform
distortion. Chebyshev's steeper skirt isn't worth the passband ripple when the
ADC already has Nyquist headroom at 500 Hz.

**Q3: How did you prevent sample loss in the DMA pipeline?**
Circular DMA with half/complete interrupts = double buffering. The DSP runs on
the idle half while the active half fills. DWT cycle counting shows ~152 us per
128-sample block vs a 256 ms refill budget - ~1900x headroom. UART TX is
interrupt-driven from a ring buffer so the DSP never blocks.

**Q4: What is CMRR and why does it matter for ECG?**
ECG is mV differential under volts of common-mode mains pickup. CMRR =
20log10(A_diff/A_cm); >80 dB at 60 Hz rejects that interference. Right-leg
drive actively cancels common mode for another 20-40 dB.

**Q5: What's the latency bottleneck and how did you measure it?**
The 128-tap FIR's group delay = (N-1)/(2 fs) = 127 ms dominates the firmware
path. It's constant and exactly known, so it's compensable. Everything else
(DSP 152 us, UART ~1 ms, network ~tens of ms) is measured with DWT, UART TC
timestamps, and browser performance.now().

## 5-minute demo script
1. Open the dashboard -> live ECG scrolling at 60 fps.
2. Touch electrodes -> noise rises on the FFT spectrum.
3. FFT view -> point out the 60 Hz spike collapsing after the notch.
4. Metrics card -> 82 dB CMRR, 0.19 uVrms noise floor, HR.
5. Click a pipeline stage -> explain it in depth.
