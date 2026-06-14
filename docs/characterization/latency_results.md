# End-to-End Latency

## Definition
Time from a feature at the electrode to its pixel appearing on the dashboard.

## Breakdown

| Segment | Contribution | How measured |
|---------|-------------|--------------|
| Analog group delay | ~2 ms | filter sim (FIR-free analog chain) |
| ADC + DMA buffering | up to 256 ms worst case per block; ~128 ms avg | block timing |
| DSP pipeline | ~152 &micro;s | DWT cycle counter |
| FIR group delay | **127 ms** (dominant) | (N-1)/(2 fs) |
| UART/BLE transmit | ~1-5 ms | UART TC timestamp |
| Network + render | ~50-84 ms | WS ping/pong + rAF |
| **Total** | **< 100-260 ms** | sum |

> The FIR's 127 ms group delay dominates the *firmware* path. It is constant
> and exactly known, so it can be compensated when aligning markers.

## Method
1. Inject a step / pacing pulse at the input.
2. Timestamp at ADC (DWT), at UART TC, and at browser render (performance.now()).
3. Difference the timestamps; the buffering term depends on where in the block
   the event lands.

## Reducing latency
- Shorten the FIR (fewer taps) - trades transition sharpness for delay.
- Process on the DMA half-interrupt (already done) rather than full buffer.
- Use a smaller block size if jitter budget allows.

## Result template

| Segment | Measured | 
|---------|----------|
| Analog | ___ ms |
| ADC/DMA | ___ ms |
| DSP | ___ &micro;s |
| FIR group delay | 127 ms |
| Link | ___ ms |
| Network/render | ___ ms |
| **Total** | ___ ms |
