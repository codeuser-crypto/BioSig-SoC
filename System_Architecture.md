# BioSig SoC — Domain, Website Integration & System Logic

> A technical companion to `PROJECT_EXPLAINED.md`. Where that file explains *what*
> the project does in plain English, this file explains the **engineering domain**
> it lives in, **how the website is wired into the hardware/firmware**, and the
> **logic** (algorithms and control flow) that makes each part work — with
> references to the real files and functions in this repo.

---

## Part A — The Project Domain

### A.1 What field is this?
This is a **biomedical mixed-signal embedded system** — it sits at the
intersection of four engineering domains:

| Domain | What it covers here | Where in the repo |
|--------|---------------------|-------------------|
| **Analog / mixed-signal electronics** | Amplifying & filtering a µV–mV biological signal, noise, CMRR | `hardware/` |
| **Embedded firmware (bare-metal)** | Register-level C on an ARM Cortex-M4, ADC/DMA/timers/UART | `firmware/` |
| **Digital Signal Processing (DSP)** | Fixed-point filters, R-peak detection, spectral analysis | `dsp/`, firmware DSP |
| **Full-stack software** | Wireless protocol, Python services, real-time web dashboard | `wireless/`, `web/` |

"**SoC**" (System on Chip) reflects that everything — acquisition, processing,
and communication — is orchestrated by a single microcontroller, the
**STM32F411** (ARM Cortex-M4 @ 168 MHz).

### A.2 The domain problem (the "why this is hard")
The signal of interest — an **electrocardiogram (ECG)** — is:
- **Tiny:** ~0.5–5 mV at the skin.
- **Low frequency:** the diagnostic band is ~0.05–150 Hz; the clinically rich
  part (QRS complex) is ~0.5–40 Hz.
- **Buried in interference:** 50/60 Hz mains hum (often *larger* than the ECG),
  motion artifact, and a ±200 mV electrode DC offset.

The domain's central metric is **SNR (signal-to-noise ratio)** and, for
common-mode interference specifically, **CMRR (common-mode rejection ratio)**.
The governing standards are **AHA** (noise < 30 µVpp) and **IEC 60601-2-47**
(patient safety + CMRR). Every design decision in this project is justified
against those numbers.

### A.3 The domain pipeline (canonical signal chain)
This is the textbook biopotential acquisition chain, and the repo implements it
end to end:

```
Transducer → Protection → Instrumentation Amp → Analog filtering → ADC
   (electrodes)             (gain + CMRR)        (HP + anti-alias)   (sampling)
        → Digital filtering → Feature extraction → Telemetry → Visualization
            (notch + BP FIR)    (R-peak/HR)        (packets)    (dashboard)
```

Understanding this chain is the key to understanding the whole project: each
folder is one or two boxes in this diagram.

---

## Part B — Website Integration

This is the part that connects the "embedded" world to the "human" world. The
website is **not** a standalone app — it's the visualization tier of a
real-time data pipeline.

### B.1 The end-to-end integration path
```
[STM32 firmware]                         [Laptop: Python]              [Browser]
 DSP → Packet_Send()                       wireless/uart_receiver.py     index.html
   → UART/BLE bytes  ──serial/BLE──►        PacketStream.feed()          + JS
                                            (CRC + seq check)             charts
                                                │
                                                ├─(option 1)─► its own WebSocket :8765
                                                │
                                            web/app.py  ──HTTP + WS :5050──►  dashboard.js
                                            (Flask + flask_sock)              ECGChart (canvas)
```

There are **two integration modes**, and the repo supports both:

1. **Self-contained demo mode (what's running now).**
   `web/app.py` has a *built-in synthetic ECG generator* (`_mock_loop()`), so the
   website runs with zero hardware. `SOURCE=mock` selects this. This is what you
   see at `http://localhost:5050`.

2. **Live hardware mode.**
   `wireless/uart_receiver.py` reads real packets from the board (`--port COM5`)
   or its own mock (`--mock`), verifies them, and re-broadcasts samples on a
   WebSocket. The dashboard (or `app.py` with `SOURCE=external` + `/api/ingest`)
   consumes that feed. The *same parsing logic* runs in both modes.

### B.2 The three integration interfaces

The browser talks to the backend over **three distinct channels**, each chosen
for the right job:

| Channel | Tech | Carries | Why this choice |
|---------|------|---------|-----------------|
| **WebSocket** `/ws` | `flask_sock` | Continuous ECG samples (high rate) | Push-based, low-overhead, no polling delay — right for 500 samples/sec |
| **REST (poll)** `/api/metrics`, `/api/status` | Flask JSON | Heart rate, SNR, latency, uptime | Slow-changing values; simple 1 Hz polling is plenty |
| **REST (on-demand)** `/api/spectrum`, `/api/filters` | Flask JSON | FFT data, filter curves | Computed when asked; spectrum polled every 0.5 s |

**Key integration principle:** *separate the firehose from the trickle.* The
high-rate waveform goes over a persistent WebSocket; the low-rate metrics go over
ordinary HTTP polling. Mixing them would either flood the metrics or throttle the
waveform.

### B.3 The WebSocket data contract
The server (`app.py`, `ws()` route) sends JSON frames. To avoid sending 500
tiny messages per second (which would overwhelm the browser), it **batches**:

```jsonc
{ "batch": [ -0.012, 0.034, 1.21, ... ] }   // up to 64 samples per frame
{ "heartbeat": true }                        // keepalive when idle
```

The client (`websocket.js`) understands `batch`, single `v`, `stats`, and
`heartbeat`, and includes **auto-reconnect with exponential backoff**
(1 s → 2 s → 4 s … capped at 30 s) so a dropped link recovers itself.

### B.4 The browser-side architecture (the front-end logic)
The front-end is deliberately split by *update rate*, because a 60 fps waveform
and a 1 Hz number need completely different rendering strategies:

| Component | File | Renders with | Why |
|-----------|------|--------------|-----|
| **ECG waveform** | `ecg_chart.js` | **raw Canvas API** | Chart.js can't keep up at 500 sps; a hand-written ring-buffer + `requestAnimationFrame` loop hits 60 fps with zero layout reflow |
| **FFT spectrum** | `spectrum.js` | **Chart.js** | Updates only ~2×/sec, so Chart.js convenience wins |
| **Filter response** | `spectrum.js` (`FilterChart`) | **Chart.js** | Static after load; toggle lines on/off |
| **Metrics + pipeline** | `dashboard.js` | DOM updates | Slow text values |

`dashboard.js` is the **conductor**: it instantiates the chart objects, opens the
WebSocket (feeding samples into `ECGChart.addSample()`), and starts the polling
timers for `/api/metrics` (1 s) and `/api/spectrum` (0.5 s). It also builds the
clickable pipeline diagram from a JS array of stage descriptions.

### B.5 Why this integration design is good
- **Decoupling:** the renderer reads from a buffer; the network fills the buffer.
  Network jitter never causes dropped animation frames (the spec's explicit goal).
- **Graceful degradation:** if `flask_sock` or `websockets` isn't installed, the
  code guards the import and the rest still runs.
- **Source-agnostic:** the dashboard doesn't know or care whether samples came
  from a real STM32, the receiver's mock, or the backend's generator — they all
  arrive as identical `{"v": ...}`/`{"batch": [...]}` messages.

---

## Part C — The System Logic (algorithms & control flow)

This section traces the actual *logic* — the rules and computations — at each
layer, with the real function names.

### C.1 Filter design logic (`dsp/filter_design.py`)
**Goal:** turn human-friendly filter specs into integer coefficients a tiny chip
can run.

1. **Design in floating point** using scipy:
   - `design_notch(f0, fs, r)` builds a 2nd-order IIR notch. Logic:
     `H(z) = (1 − 2cos(ω₀)z⁻¹ + z⁻²) / (1 − 2r·cos(ω₀)z⁻¹ + r²z⁻²)`.
     The pole radius `r` (0.985) controls how narrow the notch is — closer to 1
     = narrower. The numerator is normalized so the passband gain is ~0 dB.
   - `design_bandpass_fir(...)` uses the window method (`firwin2`, Hamming) to
     build a 128-tap linear-phase bandpass (0.5–40 Hz).
2. **Quantize to Q15** (`float_to_q15`): multiply by 32768, round, clamp to
   ±32767. Q15 = 16-bit integers representing −1.0…+1.0 — the format the chip's
   DSP instructions use.
3. **Re-layout for CMSIS** (`_biquad_to_cmsis_q15`): the ARM library wants
   `[b0, b1, b2, −a1, −a2]` and *negates* the feedback terms. Coefficients can
   exceed 1.0, so they're pre-scaled by ½ and a `postShift = 1` tells the chip to
   multiply the result back by 2.
4. **Emit C** (`export_c_header`): writes `firmware/Core/Inc/filters.h`. **The
   firmware never computes filters — it just includes this generated table.**
   This is the critical cross-domain link: *Python designs, C executes.*

### C.2 Verification logic (`dsp/verify_filters.py`)
The clever bit: it **reads back the generated `filters.h`**, reverses the Q15 +
CMSIS transforms, and re-checks the frequency response. This proves the
*quantized* filter (what the chip actually runs) still meets spec — not just the
ideal float design. It's a closed feedback loop on the toolchain itself.

### C.3 Firmware acquisition logic (`firmware/Core/Src/adc_dma.c`)
The control flow is **interrupt-driven and hands-off**:
- `TIM2` is configured to fire a trigger (TRGO) at *exactly* 500 Hz.
- Each trigger makes `ADC1` take one sample of pin PA0.
- `DMA2` automatically copies each sample into a **circular buffer** of 256
  values — no CPU involvement.
- The DMA raises an interrupt at the **half-way point** (`HTIF`) and at the
  **end** (`TCIF`). The handler just sets a flag: `dsp_buf_ready = 1` or `2`.

This is **ping-pong / double buffering**: while the DMA fills the second half,
the CPU processes the first half, and vice-versa. Nothing is ever lost.

### C.4 DSP pipeline logic (`firmware/Core/Src/dsp_pipeline.c`)
`DSP_Pipeline_Process()` runs on each 128-sample block:
1. **Convert** ADC counts → Q15: subtract the 2048 mid-rail bias, shift left 3
   (×8) to use the full integer range, and saturate.
2. **Notch** 60 Hz then 50 Hz via `arm_biquad_cascade_df1_q15` (uses the
   generated coefficients).
3. **Bandpass** via `arm_fir_q15` — this uses the Cortex-M4 SIMD `SMLAD`
   instruction to do 2 multiply-accumulates per cycle.
4. **Detect R-peaks** (`detect_rpeaks`): a simplified Pan-Tompkins —
   *differentiate → square → moving-window integrate → adaptive threshold →
   200 ms refractory*. When two peaks are found, `heart_rate_bpm = 60 / RR`.
5. **Measure itself:** the whole function is wrapped in DWT cycle-counter reads,
   storing `pipeline_cycles` (~152 µs) — the firmware profiles its own speed.
6. **Packetize:** each output sample → `Packet_Send()`.

### C.5 Wire-protocol logic (`firmware/.../packet.c` ↔ `wireless/packet_parser.py`)
The same 10-byte format is implemented on both ends so they're guaranteed
compatible:
```
[0xAA][0x55][sample LE int16][seq LE uint32][CRC-8][0xFF]
```
- **Framing logic:** two start bytes (`0xAA 0x55`) reduce the chance of a false
  sync; one end byte (`0xFF`) closes it.
- **Integrity logic (CRC-8, poly 0x07):** a 1-byte fingerprint over the payload.
  The receiver recomputes it; mismatch ⇒ drop the packet, increment `errors`.
- **Loss-detection logic (sequence number):** each packet carries a monotonic
  counter. The receiver computes `gap = seq − last_seq − 1`; any gap ⇒ that many
  packets were dropped in flight. This is how the dashboard's "packet loss %" is
  derived.
- **Resync logic** (`PacketStream.feed`): if a packet fails, it advances by one
  byte and re-hunts for `0xAA 0x55`, so a single corrupted byte doesn't desync
  the whole stream. Split packets across reads are buffered until complete.

### C.6 Backend logic (`web/app.py`)
- A background thread (`_mock_loop`, or external ingest) calls `_publish(v)`,
  which appends to a shared `ecg_history` ring buffer (last 5000 samples) and to
  each connected WebSocket's per-client queue (under a lock).
- `_metrics_loop` runs once a second: detects heart rate from recorded R-peak
  indices and estimates the noise floor from the recent signal.
- `/api/spectrum` logic: take the last 2048 samples, remove the DC mean, apply a
  **Hanning window** (reduces spectral leakage), run an FFT (`np.fft.rfft`),
  convert magnitude to dB, and return frequency/magnitude arrays. This is what
  lets you *see* the 60 Hz spike in the browser.
- `/api/filters` logic: re-derives the filter magnitude responses with scipy so
  the front-end can draw the design curves.

### C.7 Front-end rendering logic (`web/static/js/ecg_chart.js`)
- A `Float32Array(5000)` ring buffer; `addSample()` writes at `writeIdx % 5000`.
- `requestAnimationFrame` loop (`_render`) draws every frame independently of
  data arrival:
  - `_drawGrid()` paints the ECG-paper grid (minor/major lines).
  - `_drawTrace()` walks back `visibleSamples` from `writeIdx`, maps each to
    (x = time, y = mid − value × gain × scale), and strokes a glowing cyan path.
- **Logic that matters:** rendering is *pull-based* from the buffer, and
  receiving is *push-based* into the buffer. They never block each other — the
  decoupling that guarantees smooth 60 fps regardless of network timing.

---

## Part D — How the three views connect (one mental model)

```
DOMAIN says WHAT must happen:   "extract a clean ECG and show it, beating AHA noise spec"
LOGIC says HOW each step works: filters, CRC, double-buffering, FFT, ring buffers
INTEGRATION says HOW pieces talk: WebSocket firehose + REST trickle + shared buffers
```

- The **domain** dictates the requirements (gain 5000×, CMRR >80 dB, 500 sps,
  the 0.5–40 Hz band, the AHA/IEC standards).
- The **logic** is how each requirement is met (e.g. *CMRR* → 3-op-amp INA +
  right-leg drive; *anti-aliasing* → 150 Hz LP before a 500 Hz ADC; *no sample
  loss* → DMA ping-pong; *integrity* → CRC + sequence numbers).
- The **integration** is how the result becomes something a human sees in real
  time, with the firehose/trickle split and the source-agnostic message format.

---

## Part E — Quick reference: which file does what

| Concern | Primary file(s) | Key function(s) |
|---------|-----------------|------------------|
| Filter design → C header | `dsp/filter_design.py` | `design_notch`, `design_bandpass_fir`, `export_c_header` |
| Filter verification | `dsp/verify_filters.py` | `verify` |
| Noise vs medical spec | `dsp/noise_budget.py` | `compute_budget`, `rss` |
| Circuit simulation | `hardware/spice/*.py` | `generate_ecg`, `apply_ina` |
| ADC + DMA capture | `firmware/.../adc_dma.c` | `ADC_DMA_Init`, `DMA2_Stream0_IRQHandler` |
| Real-time DSP | `firmware/.../dsp_pipeline.c` | `DSP_Pipeline_Process`, `detect_rpeaks` |
| Packet build/parse | `packet.c`, `packet_parser.py` | `Packet_Send`, `PacketStream.feed` |
| Wireless receive + bridge | `wireless/uart_receiver.py` | `ECGReceiver`, `serial_source` |
| Web backend + APIs | `web/app.py` | `_publish`, `ws`, `spectrum` |
| Live waveform | `web/static/js/ecg_chart.js` | `addSample`, `_drawTrace` |
| WebSocket client | `web/static/js/websocket.js` | `ECGWebSocket._connect` |
| Dashboard conductor | `web/static/js/dashboard.js` | polling + pipeline diagram |
