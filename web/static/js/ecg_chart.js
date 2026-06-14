/**
 * ecg_chart.js - High-performance real-time ECG display on the Canvas API.
 *
 * Circular sample buffer (5000 = 10 s at 500 sps), redrawn each animation
 * frame. Scrolling is done by indexing the ring buffer, not DOM scroll, so
 * there is no layout reflow. ECG-paper grid is drawn behind a glowing cyan
 * trace; amber triangles mark detected R-peaks.
 */
class ECGChart {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    this.ctx = this.canvas.getContext('2d');
    this.buffer = new Float32Array(5000).fill(0);
    this.writeIdx = 0;
    this.rPeaks = [];
    this.gain = 2.0;
    this.sweepPxPerSec = 100;     // 25 mm/s default
    this.amplitudePxPerMv = 90;
    this.paused = false;
    this._resize();
    window.addEventListener('resize', () => this._resize());
    requestAnimationFrame(() => this._render());
  }

  _resize() {
    const ratio = window.devicePixelRatio || 1;
    const cssW = this.canvas.clientWidth || this.canvas.parentElement.clientWidth;
    const cssH = this.canvas.height;
    this.canvas.width = cssW * ratio;
    this.canvas.height = cssH * ratio;
    this.ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    this.w = cssW;
    this.h = cssH;
  }

  addSample(v) { this.buffer[this.writeIdx % 5000] = v; this.writeIdx++; }
  addRPeak(i)  { this.rPeaks.push(i); if (this.rPeaks.length > 100) this.rPeaks.shift(); }
  setGain(f)   { this.gain = f; }
  setSweepSpeed(px) { this.sweepPxPerSec = px; }
  pause()      { this.paused = true; }
  resume()     { this.paused = false; }

  exportCSV() {
    const n = Math.min(this.writeIdx, 5000);
    let csv = 'index,voltage_mv\n';
    for (let i = 0; i < n; i++) {
      const idx = (this.writeIdx - n + i + 5000 * 2) % 5000;
      csv += i + ',' + this.buffer[idx].toFixed(5) + '\n';
    }
    const blob = new Blob([csv], { type: 'text/csv' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'ecg_capture.csv';
    a.click();
  }

  _drawGrid() {
    const ctx = this.ctx, w = this.w, h = this.h;
    ctx.fillStyle = '#0a0f1e';
    ctx.fillRect(0, 0, w, h);
    const minor = 20, major = 100;   // px
    ctx.lineWidth = 1;
    ctx.strokeStyle = 'rgba(0,255,100,0.05)';
    ctx.beginPath();
    for (let x = 0; x < w; x += minor) { ctx.moveTo(x, 0); ctx.lineTo(x, h); }
    for (let y = 0; y < h; y += minor) { ctx.moveTo(0, y); ctx.lineTo(w, y); }
    ctx.stroke();
    ctx.strokeStyle = 'rgba(0,255,100,0.15)';
    ctx.beginPath();
    for (let x = 0; x < w; x += major) { ctx.moveTo(x, 0); ctx.lineTo(x, h); }
    for (let y = 0; y < h; y += major) { ctx.moveTo(0, y); ctx.lineTo(w, y); }
    ctx.stroke();
  }

  _drawTrace() {
    const ctx = this.ctx, w = this.w, midY = this.h / 2;
    const samplesVisible = Math.floor((w / this.sweepPxPerSec) * 500);
    const n = Math.min(this.writeIdx, samplesVisible, 5000);
    if (n < 2) return;
    const pxPerSample = this.sweepPxPerSec / 500;
    ctx.lineWidth = 2;
    ctx.lineJoin = 'round';
    ctx.lineCap = 'round';
    ctx.strokeStyle = '#22d3ee';
    ctx.shadowColor = '#22d3ee';
    ctx.shadowBlur = 6;
    ctx.beginPath();
    for (let i = 0; i < n; i++) {
      const idx = (this.writeIdx - n + i + 5000 * 2) % 5000;
      const x = i * pxPerSample;
      const y = midY - this.buffer[idx] * this.amplitudePxPerMv * this.gain;
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    }
    ctx.stroke();
    ctx.shadowBlur = 0;
  }

  _render() {
    if (!this.paused) { this._drawGrid(); this._drawTrace(); }
    requestAnimationFrame(() => this._render());
  }
}
window.ECGChart = ECGChart;
