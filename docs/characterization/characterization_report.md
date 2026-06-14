# ECG System Characterization Report

Source: **synthesized capture (no --csv given)**, 10.0 s @ 500 Hz

| Metric | Measured | Target | Result |
|---|---|---|---|
| Noise floor | 4.79 uVrms | < 10.6 uVrms | PASS |
| 60 Hz notch attenuation | 10.7 dB | > 20 dB | FAIL |
| Heart rate | 72 BPM | 40-180 BPM | PASS |
| R-peaks detected | 11 | - | - |
| SNR | 43.4 dB | > 40 dB | PASS |

## Methodology

- **Noise floor:** RMS of the first 1 s with inputs shorted.
- **Notch:** ratio of the 60 Hz FFT bin to the 15 Hz QRS-band bin.
- **Heart rate:** Pan-Tompkins style derivative-square-integrate R-peak detection with a 200 ms refractory period.
- **SNR:** half peak-to-peak signal over quiet-segment RMS noise.
