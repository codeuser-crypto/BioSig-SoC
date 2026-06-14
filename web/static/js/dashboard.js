/**
 * dashboard.js - Wires the canvas chart, spectrum, filters, metrics polling,
 * pipeline diagram and controls together.
 */
(function () {
  const ecg = new ECGChart('ecg-canvas');
  const spectrum = new SpectrumChart('spectrum-canvas');
  const filters = new FilterChart('filters-canvas');

  // HR sparkline (Chart.js)
  const hrSpark = new Chart(document.getElementById('hr-spark').getContext('2d'), {
    type: 'line',
    data: { labels: [], datasets: [{ data: [], borderColor: '#10b981', borderWidth: 2, pointRadius: 0, tension: 0.3 }] },
    options: { animation: false, responsive: true, maintainAspectRatio: false,
      scales: { x: { display: false }, y: { display: false } },
      plugins: { legend: { display: false } } },
  });
  const hrHistory = [];

  // --- WebSocket sample stream ---
  const wsUrl = (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws';
  new ECGWebSocket(wsUrl, (batch) => {
    for (const v of batch) ecg.addSample(v);
  }, (stats) => {
    if (stats.loss_pct !== undefined) document.getElementById('m-loss').textContent = stats.loss_pct;
  });

  window.addEventListener('ws-status', (e) => {
    const pill = document.getElementById('pill-conn');
    const dot = pill.querySelector('.dot');
    if (e.detail === 'connected') { pill.childNodes[1].textContent = ' CONNECTED'; dot.className = 'dot ok'; }
    else { pill.childNodes[1].textContent = ' RECONNECTING'; dot.className = 'dot bad'; }
  });

  // --- Controls ---
  document.getElementById('btn-pause').onclick = () => ecg.pause();
  document.getElementById('btn-play').onclick = () => ecg.resume();
  document.getElementById('btn-export').onclick = () => ecg.exportCSV();
  document.querySelectorAll('.gain').forEach(b => b.onclick = () => {
    document.querySelectorAll('.gain').forEach(x => x.classList.remove('active'));
    b.classList.add('active'); ecg.setGain(parseFloat(b.dataset.gain));
  });
  document.querySelectorAll('.sweep').forEach(b => b.onclick = () => {
    document.querySelectorAll('.sweep').forEach(x => x.classList.remove('active'));
    b.classList.add('active'); ecg.setSweepSpeed(parseInt(b.dataset.sweep));
  });
  document.querySelectorAll('.toggles input').forEach(cb => cb.onchange = () =>
    filters.toggle(cb.dataset.f, cb.checked));

  // --- Periodic API polling ---
  function fmtUptime(s) {
    const h = String(Math.floor(s / 3600)).padStart(2, '0');
    const m = String(Math.floor((s % 3600) / 60)).padStart(2, '0');
    const sec = String(s % 60).padStart(2, '0');
    return `${h}:${m}:${sec}`;
  }

  async function pollMetrics() {
    try {
      const m = await (await fetch('/api/metrics')).json();
      document.getElementById('m-hr').textContent = m.hr_bpm || '--';
      document.getElementById('hr-header').textContent = m.hr_bpm || '--';
      document.getElementById('m-snr').textContent = m.snr_db;
      document.getElementById('m-noise').textContent = m.noise_floor_uvrms;
      document.getElementById('m-cmrr').textContent = m.cmrr_db;
      document.getElementById('m-lat').textContent = m.latency_ms;
      document.getElementById('m-net').textContent = Math.max(0, m.latency_ms - 3).toFixed(0);
      if (m.hr_bpm) {
        hrHistory.push(m.hr_bpm); if (hrHistory.length > 30) hrHistory.shift();
        hrSpark.data.labels = hrHistory.map((_, i) => i);
        hrSpark.data.datasets[0].data = hrHistory;
        const hrEl = document.querySelector('#m-hr');
        const c = (m.hr_bpm >= 60 && m.hr_bpm <= 100) ? '#10b981' :
                  (m.hr_bpm >= 40 && m.hr_bpm <= 120) ? '#f59e0b' : '#ef4444';
        hrEl.parentElement.style.color = c;
        hrSpark.update('none');
      }
    } catch (e) {}
    try {
      const s = await (await fetch('/api/status')).json();
      document.getElementById('m-link').textContent = s.connected ? 'Connected' : 'Offline';
      document.getElementById('m-uptime').textContent = fmtUptime(s.uptime_s);
      document.getElementById('pill-source').textContent = s.source.toUpperCase();
      document.getElementById('m-loss').textContent = s.packet_loss_pct;
    } catch (e) {}
  }

  async function pollSpectrum() {
    try {
      const d = await (await fetch('/api/spectrum')).json();
      if (d.freqs.length) spectrum.update(d.freqs, d.magnitudes);
    } catch (e) {}
  }

  async function loadFilters() {
    try { filters.load(await (await fetch('/api/filters')).json()); } catch (e) {}
  }

  // --- Pipeline diagram ---
  const stages = [
    { name: 'Electrodes', cls: 'analog', spec: 'Ag/AgCl, 3-lead',
      detail: '<b>Electrodes:</b> Skin-contact Ag/AgCl with patient-protection 5.1k series + clamp diodes (IEC 60601). Signal 0.5-5 mV, +200 mV DC offset.' },
    { name: 'INA', cls: 'analog', spec: '500x, CMRR>80dB',
      detail: '<b>Instrumentation amp:</b> 3-op-amp (OPA2134), gain 1+50k/Rg = 500x, CMRR >80 dB rejects 60 Hz common-mode. Right-leg drive feeds back inverted common mode.' },
    { name: 'HP Filter', cls: 'analog', spec: '0.05 Hz',
      detail: '<b>High-pass 0.05 Hz:</b> 3.3uF film + 1M sets fc=0.048 Hz, removes electrode DC offset and baseline wander without distorting ST segment.' },
    { name: 'LP Filter', cls: 'analog', spec: '150 Hz, 2nd order',
      detail: '<b>Anti-alias LP:</b> 2nd-order Sallen-Key Butterworth, fc=150 Hz, Q=0.707 maximally flat passband prevents aliasing at the 250 Hz Nyquist.' },
    { name: 'ADC+DMA', cls: 'digital', spec: '12-bit, 500 sps',
      detail: '<b>ADC + DMA:</b> STM32F411 ADC1 triggered by TIM2 TRGO at exactly 500 Hz, DMA2 circular buffer, half/full-transfer IRQ for double-buffered block processing.' },
    { name: 'DSP', cls: 'digital', spec: 'FIR+notch, 152us',
      detail: '<b>DSP pipeline:</b> dual IIR notch (50/60 Hz) + 128-tap Q15 FIR bandpass via CMSIS-DSP SIMD, Pan-Tompkins R-peak detection, 152 us/block measured by DWT.' },
    { name: 'BLE/UART', cls: 'wireless', spec: '40 kbps, CRC-8',
      detail: '<b>Wireless link:</b> 10-byte framed packets (0xAA 0x55 ... CRC-8 0xFF), sequence numbers for loss detection, 40 kbps over BLE NUS or 115200 UART.' },
    { name: 'Dashboard', cls: 'wireless', spec: '<100 ms e2e',
      detail: '<b>Dashboard:</b> Python receiver verifies CRC/sequence, bridges to this browser over WebSocket; Canvas trace renders at 60 fps, <100 ms electrode-to-pixel.' },
  ];
  const pl = document.getElementById('pipeline');
  const detail = document.getElementById('pipeline-detail');
  stages.forEach((s, i) => {
    const el = document.createElement('div');
    el.className = `stage ${s.cls}`;
    el.innerHTML = `<div class="stage-name">${s.name}</div><div class="stage-spec">${s.spec}</div>`;
    el.onclick = () => {
      document.querySelectorAll('.stage').forEach(x => x.classList.remove('active'));
      el.classList.add('active');
      detail.innerHTML = s.detail;
    };
    pl.appendChild(el);
  });

  loadFilters();
  setInterval(pollMetrics, 1000);
  setInterval(pollSpectrum, 500);
  pollMetrics();
})();
