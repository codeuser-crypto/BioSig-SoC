/**
 * spectrum.js - FFT spectrum analyzer and the static filter-response chart,
 * both rendered with Chart.js (slow-updating, so Chart.js is fine here).
 */
class SpectrumChart {
  constructor(canvasId) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    this.chart = new Chart(ctx, {
      type: 'line',
      data: { labels: [], datasets: [{
        label: 'Spectrum', data: [], borderColor: '#22d3ee',
        borderWidth: 1.5, pointRadius: 0, fill: false, tension: 0.1,
      }] },
      options: {
        animation: false, responsive: true, maintainAspectRatio: false,
        scales: {
          x: { type: 'linear', min: 0, max: 150,
               title: { display: true, text: 'Frequency (Hz)', color: '#94a3b8' },
               ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } },
          y: { min: -80, max: 0,
               title: { display: true, text: 'dB', color: '#94a3b8' },
               ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } },
        },
        plugins: { legend: { display: false },
          annotation: undefined },
      },
    });
  }
  update(freqs, mags) {
    const pts = freqs.map((f, i) => ({ x: f, y: mags[i] }));
    this.chart.data.datasets[0].data = pts;
    this.chart.update('none');
  }
}

class FilterChart {
  constructor(canvasId) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    this.chart = new Chart(ctx, {
      type: 'line',
      data: { datasets: [
        { label: 'FIR 0.5-40Hz', key: 'fir', data: [], borderColor: '#22d3ee', borderWidth: 1.5, pointRadius: 0 },
        { label: '60Hz notch', key: 'notch60', data: [], borderColor: '#f59e0b', borderWidth: 1.5, pointRadius: 0 },
        { label: '50Hz notch', key: 'notch50', data: [], borderColor: '#ef4444', borderWidth: 1.5, borderDash: [4,3], pointRadius: 0 },
      ] },
      options: {
        animation: false, responsive: true, maintainAspectRatio: false,
        scales: {
          x: { type: 'linear', min: 0, max: 150,
               title: { display: true, text: 'Frequency (Hz)', color: '#94a3b8' },
               ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } },
          y: { min: -80, max: 5,
               title: { display: true, text: 'dB', color: '#94a3b8' },
               ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } },
        },
        plugins: { legend: { labels: { color: '#94a3b8', boxWidth: 12 } } },
      },
    });
  }
  load(data) {
    const f = data.freqs;
    for (const ds of this.chart.data.datasets) {
      ds.data = f.map((x, i) => ({ x, y: data[ds.key][i] }));
    }
    this.chart.update('none');
  }
  toggle(key, visible) {
    const ds = this.chart.data.datasets.find(d => d.key === key);
    if (ds) { ds.hidden = !visible; this.chart.update('none'); }
  }
}
window.SpectrumChart = SpectrumChart;
window.FilterChart = FilterChart;
