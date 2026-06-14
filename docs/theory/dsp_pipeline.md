# DSP Pipeline Implementation Notes

Target: STM32F411 Cortex-M4F @ 168 MHz, CMSIS-DSP, Q15 fixed point.

## Data flow
```
TIM2 TRGO (500 Hz) -> ADC1 -> DMA2 circular buffer[256]
       half-transfer IRQ -> process first 128 samples
       full-transfer IRQ -> process second 128 samples
```
Double buffering: while the DMA fills one half, the CPU processes the other.
At 500 Hz a 128-sample block arrives every 256 ms, so the DSP has a huge
timing margin.

## Per-block stages
| Stage | Operation | ~cycles | ~time |
|-------|-----------|---------|-------|
| 1 | ADC counts -> Q15 (bias remove, <<3) | 640 | 3.8 us |
| 2 | 60 Hz IIR notch (biquad cascade) | 640 | 3.8 us |
| 3 | 50 Hz IIR notch (biquad cascade) | 640 | 3.8 us |
| 4 | 128-tap FIR bandpass (SIMD SMLAD) | ~8200 | ~49 us |
| 5 | Pan-Tompkins R-peak detection | 2560 | 15 us |
| 6 | packetize + queue | 1280 | 7.6 us |
| | **Total** | | **~132 us** |

Measured live with the DWT cycle counter (`pipeline_cycles`), reported over
UART every 10 s. 132 us << 256 ms budget -> ~1900x headroom.

## Fixed-point format
- Q15: 1 sign bit + 15 fractional bits, range [-1.0, +1.0) = [-32768, 32767].
- ADC 12-bit (0-4095), mid-rail 2048. `q15 = (count - 2048) << 3` maps the
  &plusmn;1.65 V window to near full Q15 scale.
- Always use `arm_biquad_cascade_df1_q15` and `arm_fir_q15` - they are SIMD
  optimized (SMLAD = 2 MACs/cycle) and handle saturation correctly.

## R-peak detection (simplified Pan-Tompkins)
Differentiate -> square -> moving-window integrate (~150 ms / 75 samples) ->
adaptive threshold with a 200 ms refractory period. Updates `heart_rate_bpm`
from the running RR interval.

## ISR discipline
- All ISRs except the DMA half/complete handler are < 10 us.
- The DSP runs in the main loop (woken via WFI), not inside the DMA ISR, so the
  ISR just sets `dsp_buf_ready`.
- UART TX is interrupt-driven from a circular buffer; the DSP never blocks on
  the UART.
