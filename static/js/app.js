// AimSmile — Dashboard & Neumorphic Interactions

document.addEventListener('DOMContentLoaded', function () {
  // Sidebar toggle (mobile)
  const sidebar = document.querySelector('.sidebar');
  const backdrop = document.querySelector('.sidebar-backdrop');
  const burger = document.querySelector('.hamburger');
  if (burger) {
    burger.addEventListener('click', () => {
      sidebar?.classList.toggle('open');
      backdrop?.classList.toggle('show');
    });
  }
  if (backdrop) {
    backdrop.addEventListener('click', () => {
      sidebar?.classList.remove('open');
      backdrop?.classList.remove('show');
    });
  }

  // Auto-dismiss flash messages
  document.querySelectorAll('[data-autohide]').forEach((el) => {
    setTimeout(() => {
      el.style.transition = 'opacity .4s';
      el.style.opacity = '0';
      setTimeout(() => el.remove(), 400);
    }, 4000);
  });

  // Dark/Light Theme toggle
  const themeToggle = document.getElementById('themeToggleBtn');
  const html = document.documentElement;
  const savedTheme = localStorage.getItem('aimsmile-theme');

  if (savedTheme === 'dark') {
    html.classList.add('dark-theme');
  }

  if (themeToggle) {
    const icon = themeToggle.querySelector('i');
    if (html.classList.contains('dark-theme')) {
      icon?.classList.remove('bi-moon');
      icon?.classList.add('bi-sun');
    }

    themeToggle.addEventListener('click', function() {
      const iconEl = this.querySelector('i');
      if (html.classList.contains('dark-theme')) {
        html.classList.remove('dark-theme');
        localStorage.setItem('aimsmile-theme', 'light');
        if (iconEl) {
          iconEl.classList.remove('bi-sun');
          iconEl.classList.add('bi-moon');
        }
      } else {
        html.classList.add('dark-theme');
        localStorage.setItem('aimsmile-theme', 'dark');
        if (iconEl) {
          iconEl.classList.remove('bi-moon');
          iconEl.classList.add('bi-sun');
        }
      }
    });
  }
});

// Chart palette helper
const DC = {
  colors: {
    primary: '#2e68db',
    primaryLight: '#e0ebf8',
    accent: '#06b6d4',
    palette: ['#2e68db', '#0d9488', '#8b5cf6', '#f59e0b', '#ec4899', '#3b82f6'],
  },
};

function readJSON(id) {
  const el = document.getElementById(id);
  if (!el) return null;
  try { return JSON.parse(el.textContent); } catch (e) { return null; }
}

function gradientFill(ctx, color) {
  const g = ctx.createLinearGradient(0, 0, 0, 260);
  g.addColorStop(0, 'rgba(46, 104, 219, 0.22)');
  g.addColorStop(0.7, 'rgba(46, 104, 219, 0.05)');
  g.addColorStop(1, 'rgba(46, 104, 219, 0.0)');
  return g;
}

// Chart.js plugin to draw values above peak dots (matching screenshot)
const peakCalloutPlugin = {
  id: 'peakCallout',
  afterDatasetsDraw(chart) {
    const { ctx } = chart;
    chart.data.datasets.forEach((dataset, datasetIndex) => {
      const meta = chart.getDatasetMeta(datasetIndex);
      if (!meta.visible) return;
      meta.data.forEach((element, index) => {
        const val = dataset.data[index];
        if (val > 0) {
          ctx.save();
          ctx.font = '700 11px Inter, sans-serif';
          ctx.fillStyle = '#2e68db';
          ctx.textAlign = 'center';
          ctx.textBaseline = 'bottom';
          let labelText = val;
          if (typeof val === 'number') {
            if (val >= 100) {
              labelText = '₱' + Math.round(val);
            } else {
              labelText = val.toString();
            }
          }
          ctx.fillText(labelText, element.x, element.y - 7);
          ctx.restore();
        }
      });
    });
  }
};

function lineChart(canvasId, dataId, label) {
  const canvas = document.getElementById(canvasId);
  const data = readJSON(dataId);
  if (!canvas || !data) return;
  const ctx = canvas.getContext('2d');
  
  new Chart(ctx, {
    type: 'line',
    data: {
      labels: data.labels,
      datasets: [{
        label: label || '',
        data: data.data,
        borderColor: DC.colors.primary,
        backgroundColor: gradientFill(ctx, DC.colors.primary),
        fill: true,
        tension: 0.44,
        borderWidth: 2.8,
        pointBackgroundColor: DC.colors.primary,
        pointBorderColor: '#ffffff',
        pointBorderWidth: 1.5,
        pointRadius: data.data.map(v => v > 0 ? 4.5 : 0),
        pointHoverRadius: 6,
      }],
    },
    options: {
      ...baseOptions(),
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#1e293b',
          titleFont: { size: 11, weight: '700' },
          bodyFont: { size: 12 },
          padding: 8,
          cornerRadius: 8,
          callbacks: {
            label: function(ctx) {
              return (ctx.parsed.y >= 100 ? '₱' : '') + ctx.parsed.y.toLocaleString();
            }
          }
        }
      }
    },
    plugins: [peakCalloutPlugin],
  });
}

function barChart(canvasId, dataId, label) {
  const canvas = document.getElementById(canvasId);
  const data = readJSON(dataId);
  if (!canvas || !data) return;
  new Chart(canvas.getContext('2d'), {
    type: 'bar',
    data: {
      labels: data.labels,
      datasets: [{
        label: label || '',
        data: data.data,
        backgroundColor: DC.colors.primary,
        borderRadius: 8,
        maxBarThickness: 16,
      }],
    },
    options: {
      ...baseOptions(),
      scales: {
        x: {
          grid: { display: false },
          ticks: {
            color: '#94a3b8',
            font: { size: 10 },
            maxRotation: 0,
            callback: function(val, index) {
              // Show fewer labels on x-axis like Dec 25, Mar 26, Jun 26, Sep 26, Nov 26
              const labels = data.labels;
              if (index === 0 || index === labels.length - 1 || index % 3 === 0) {
                return labels[index];
              }
              return '';
            }
          },
          border: { display: false },
        },
        y: {
          grid: { color: 'rgba(163, 177, 198, 0.18)' },
          ticks: { color: '#94a3b8', font: { size: 10 }, stepSize: 0.5 },
          beginAtZero: true,
          border: { display: false },
        },
      }
    },
  });
}

function doughnutChart(canvasId, dataId) {
  const canvas = document.getElementById(canvasId);
  const data = readJSON(dataId);
  if (!canvas) return;

  const labels = (data && data.labels && data.labels.length) ? data.labels : ['Appointments'];
  const values = (data && data.data && data.data.length && data.data.some(v => v > 0)) ? data.data : [1];

  new Chart(canvas.getContext('2d'), {
    type: 'doughnut',
    data: {
      labels: labels,
      datasets: [{
        data: values,
        backgroundColor: values.length === 1 || values.filter(v => v > 0).length === 1 ? [DC.colors.primary] : DC.colors.palette,
        borderWidth: 0,
        hoverOffset: 3,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '74%',
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#1e293b',
          cornerRadius: 8,
          bodyFont: { size: 11 }
        }
      },
    },
  });
}

function baseOptions() {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      x: {
        grid: { display: false },
        ticks: { color: '#94a3b8', font: { size: 10 } },
        border: { display: false },
      },
      y: {
        grid: { color: 'rgba(163, 177, 198, 0.18)', strokeDashArray: [4, 4] },
        ticks: { color: '#94a3b8', font: { size: 10 } },
        beginAtZero: true,
        border: { display: false },
      },
    },
  };
}

// Dynamic formset helper
function addFormsetRow(prefix) {
  const totalForms = document.querySelector(`#id_${prefix}-TOTAL_FORMS`);
  const container = document.querySelector(`#${prefix}-rows`);
  const template = document.querySelector(`#${prefix}-empty`);
  if (!totalForms || !container || !template) return;
  const index = parseInt(totalForms.value, 10);
  const html = template.innerHTML.replace(/__prefix__/g, index);
  const wrapper = document.createElement('div');
  wrapper.innerHTML = html;
  container.appendChild(wrapper);
  totalForms.value = index + 1;
}
