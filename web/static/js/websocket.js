/**
 * websocket.js - WebSocket client with auto-reconnect (exponential backoff).
 *
 * Server messages:
 *   {"batch": [v0, v1, ...]}  - a batch of mV samples
 *   {"v": 0.23}               - a single sample (compat)
 *   {"stats": {...}}          - receiver statistics
 *   {"heartbeat": true}       - keepalive when idle
 */
class ECGWebSocket {
  constructor(url, onSamples, onStats) {
    this.url = url;
    this.onSamples = onSamples;
    this.onStats = onStats;
    this.reconnectDelay = 1000;
    this.sampleCount = 0;
    this._connect();
  }
  _connect() {
    try { this.ws = new WebSocket(this.url); }
    catch (e) { this._scheduleReconnect(); return; }
    this.ws.onopen = () => {
      this.reconnectDelay = 1000;
      window.dispatchEvent(new CustomEvent('ws-status', { detail: 'connected' }));
    };
    this.ws.onmessage = (ev) => {
      const d = JSON.parse(ev.data);
      if (d.batch) { this.onSamples(d.batch); this.sampleCount += d.batch.length; }
      else if (d.v !== undefined) { this.onSamples([d.v]); this.sampleCount++; }
      if (d.stats) this.onStats(d.stats);
    };
    this.ws.onclose = () => {
      window.dispatchEvent(new CustomEvent('ws-status', { detail: 'reconnecting' }));
      this._scheduleReconnect();
    };
    this.ws.onerror = () => { try { this.ws.close(); } catch (e) {} };
  }
  _scheduleReconnect() {
    setTimeout(() => this._connect(), this.reconnectDelay);
    this.reconnectDelay = Math.min(this.reconnectDelay * 2, 30000);
  }
}
window.ECGWebSocket = ECGWebSocket;
