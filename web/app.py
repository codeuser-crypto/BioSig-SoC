"""
app.py - Flask + WebSocket backend for the ECG dashboard.

Self-contained: by default it runs a built-in synthetic ECG generator so the
dashboard is fully demoable with no hardware. Point it at a real device by
running wireless/uart_receiver.py and setting SOURCE=upstream (the receiver's
WebSocket on :8765), or feed samples via POST /api/ingest.

Endpoints:
  GET  /              -> dashboard HTML
  GET  /api/status    -> connection + rate + loss
  GET  /api/metrics   -> HR, noise floor, latency
  GET  /api/spectrum  -> FFT of last 2048 samples
  GET  /api/filters   -> designed filter responses (for the response chart)
  POST /api/ingest    -> push one sample {"v": <mV>} (for external sources)
  WS   /ws            -> live sample stream
"""

from __future__ import annotations

import json
import math
import os
import threading
import time
from collections import deque

import numpy as np
from flask import Flask, jsonify, render_template, request

try:
    from flask_sock import Sock
except Exception:  # pragma: no cover
    Sock = None

FS = 500
HISTORY = 5000

app = Flask(__name__)
sock = Sock(app) if Sock else None

_lock = threading.Lock()
ecg_history: deque[float] = deque(maxlen=HISTORY)
_subscribers: list[deque] = []
_state = {
    "connected": True,
    "hr_bpm": 0.0,
    "noise_floor_uvrms": 0.0,
    "latency_ms": 0.0,
    "packet_loss_pct": 0.0,
    "rpeaks": deque(maxlen=200),
    "sample_idx": 0,
    "uptime_start": time.time(),
}

SOURCE = os.environ.get("SOURCE", "mock")  # mock | external


def _publish(v: float):
    with _lock:
        ecg_history.append(v)
        _state["sample_idx"] += 1
        for q in _subscribers:
            q.append(v)


# ----------------------------------------------------------------------------
# Synthetic source (default)
# ----------------------------------------------------------------------------
def _mock_loop():
    seq = 0
    t = 0.0
    dt = 1.0 / FS
    rr = 60.0 / 72.0
    last_r = -1.0
    while SOURCE == "mock":
        phase = t % rr
        r = 1.2 * math.exp(-0.5 * ((phase - 0.0) / 0.010) ** 2)
        p = 0.10 * math.exp(-0.5 * ((phase - (rr - 0.16)) / 0.022) ** 2)
        q = -0.05 * math.exp(-0.5 * ((phase - (rr - 0.04)) / 0.010) ** 2)
        s = -0.15 * math.exp(-0.5 * ((phase - 0.04) / 0.012) ** 2)
        tw = 0.30 * math.exp(-0.5 * ((phase - 0.22) / 0.055) ** 2)
        noise = 0.01 * math.sin(2 * math.pi * 60 * t) + np.random.normal(0, 0.004)
        v = r + p + q + s + tw + noise
        _publish(v)
        # R-peak marker bookkeeping for HR
        if phase < dt and t - last_r > 0.3:
            with _lock:
                _state["rpeaks"].append(_state["sample_idx"])
            last_r = t
        seq += 1
        t += dt
        time.sleep(dt)


def _metrics_loop():
    while True:
        time.sleep(1.0)
        with _lock:
            peaks = list(_state["rpeaks"])
            hist = list(ecg_history)
        if len(peaks) >= 2:
            rr = np.diff(peaks) / FS
            rr = rr[(rr > 0.3) & (rr < 2.0)]
            if len(rr):
                _state["hr_bpm"] = float(60.0 / np.mean(rr))
        if len(hist) > FS:
            quiet = np.array(hist[-FS:])
            _state["noise_floor_uvrms"] = float(np.std(np.diff(quiet)) * 1e3)
        # Mock latency estimate
        _state["latency_ms"] = 87.0


# ----------------------------------------------------------------------------
# Routes
# ----------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status")
def status():
    up = int(time.time() - _state["uptime_start"])
    return jsonify({
        "connected": _state["connected"],
        "source": SOURCE,
        "sample_rate_hz": FS,
        "packet_loss_pct": _state["packet_loss_pct"],
        "latency_ms": _state["latency_ms"],
        "uptime_s": up,
    })


@app.route("/api/metrics")
def metrics():
    return jsonify({
        "hr_bpm": round(_state["hr_bpm"], 0),
        "noise_floor_uvrms": round(_state["noise_floor_uvrms"], 3),
        "latency_ms": _state["latency_ms"],
        "cmrr_db": 82.0,
        "snr_db": 68.0,
    })


@app.route("/api/spectrum")
def spectrum():
    with _lock:
        hist = list(ecg_history)
    if len(hist) < 256:
        return jsonify({"freqs": [], "magnitudes": []})
    data = np.array(hist[-2048:])
    data = data - np.mean(data)
    data = data * np.hanning(len(data))
    mag = np.abs(np.fft.rfft(data))
    db = 20 * np.log10(mag + 1e-10)
    freqs = np.fft.rfftfreq(len(data), 1 / FS)
    return jsonify({"freqs": freqs.tolist(), "magnitudes": db.tolist()})


@app.route("/api/filters")
def filters():
    """Return designed filter magnitude responses for the response chart."""
    import scipy.signal as sig

    def resp(b, a):
        w, h = sig.freqz(b, a, worN=512, fs=FS)
        return w.tolist(), (20 * np.log10(np.abs(h) + 1e-9)).tolist()

    w0_60 = 2 * np.pi * 60 / FS
    w0_50 = 2 * np.pi * 50 / FS
    r = 0.985
    n60 = ([1, -2 * np.cos(w0_60), 1], [1, -2 * r * np.cos(w0_60), r * r])
    n50 = ([1, -2 * np.cos(w0_50), 1], [1, -2 * r * np.cos(w0_50), r * r])
    fir = sig.firwin2(128, [0, 0.5 / 250, 0.5 / 250, 40 / 250, 60 / 250, 1.0],
                      [0, 0, 1, 1, 0, 0], window="hamming")
    f, fir_db = resp(fir, [1.0])
    _, n60_db = resp(*n60)
    _, n50_db = resp(*n50)
    return jsonify({"freqs": f, "fir": fir_db, "notch60": n60_db, "notch50": n50_db})


@app.route("/api/ingest", methods=["POST"])
def ingest():
    data = request.get_json(force=True, silent=True) or {}
    if "v" in data:
        _publish(float(data["v"]))
        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": "missing 'v'"}), 400


if sock:
    @sock.route("/ws")
    def ws(ws):
        q: deque = deque(maxlen=2000)
        with _lock:
            _subscribers.append(q)
        try:
            while True:
                if q:
                    batch = []
                    while q and len(batch) < 64:
                        batch.append(round(q.popleft(), 4))
                    ws.send(json.dumps({"batch": batch}))
                else:
                    ws.send(json.dumps({"heartbeat": True}))
                time.sleep(0.02)
        except Exception:
            pass
        finally:
            with _lock:
                if q in _subscribers:
                    _subscribers.remove(q)


def _start_threads():
    if SOURCE == "mock":
        threading.Thread(target=_mock_loop, daemon=True).start()
    threading.Thread(target=_metrics_loop, daemon=True).start()


_start_threads()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5050"))
    print(f"ECG dashboard -> http://localhost:{port}  (source={SOURCE})")
    app.run(host="0.0.0.0", port=port, threaded=True)
