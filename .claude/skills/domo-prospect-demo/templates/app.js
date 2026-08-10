const THEME_KEY = '<COMPANY_SLUG>-demo-theme';

const BRAND = {
  name: "<COMPANY_NAME>",
  subtitle: "<ONE_LINE_DESCRIPTION>",
  logoUrl: <LOGO_URL_OR_null>,
};

const PALETTE = { primary: "<PRIMARY_HEX>", secondary: "<SECONDARY_HEX>", accent: "<ACCENT_HEX>" };

const MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];

// Exactly 3 category names for the breakdown dimension — these double as the
// options for the second filter (the first filter is always the Period
// selector below). Pick a dimension that fits the industry, e.g. "Service
// Line" (Tax / Assurance / Advisory), "Region" (NA / EMEA / APAC), "Business
// Unit" (Enterprise / Mid-Market / SMB), "Product Line", etc.
const ALL_CATEGORIES_LABEL = "<ALL_CATEGORIES_LABEL>"; // e.g. "All Service Lines"

const MONTHLY_BY_CATEGORY = {
  // One 12-point monthly array per category. Give each category a distinct,
  // plausible shape (seasonality, growth curve) rather than flat lines —
  // e.g. a tax-prep category spikes in Mar/Apr, a subscription category
  // grows steadily. Values are in whatever unit the trend KPI/chart uses
  // (e.g. $M revenue, unit count).
  // "<CATEGORY_1>": [12 numbers],
  // "<CATEGORY_2>": [12 numbers],
  // "<CATEGORY_3>": [12 numbers],
};

const CATEGORIES = ["<ALL_CATEGORIES_LABEL>", ...Object.keys(MONTHLY_BY_CATEGORY)];

const PERIODS = [
  { label: "Last 3 Months", months: 3 },
  { label: "Last 6 Months", months: 6 },
  { label: "Last 12 Months (FY)", months: 12 },
];

// One entry per KPI tile (match the count the user chose in step 3).
const KPI_META = [
  // { key: "activeWorkOrders", label: "Active Work Orders" },
];

// One block per entry in CATEGORIES (i.e. ALL_CATEGORIES_LABEL + each of the
// 3 category names). Every KPI in KPI_META needs a value/delta/spark here for
// every category — plausible proportional differences per category, not just
// the same number scaled uniformly. `spark` is a short (5-6 point) trend
// array used to draw a mini sparkline under the KPI value; it does not need
// to be derived from MONTHLY_BY_CATEGORY, just directionally consistent with
// `delta`.
const KPI_DATA = {
  // "<ALL_CATEGORIES_LABEL>": {
  //   activeWorkOrders: { value: "1,284", delta: 12.4, spark: [1080,1120,1160,1210,1250,1284] },
  // },
  // "<CATEGORY_1>": { ... },
  // "<CATEGORY_2>": { ... },
  // "<CATEGORY_3>": { ... },
};

const BREAKDOWN_LABELS = Object.keys(MONTHLY_BY_CATEGORY);
const BREAKDOWN_COLOR_BY_CATEGORY = {
  // Map each of the 3 category names to one of the 3 palette colors 1:1.
  // "<CATEGORY_1>": PALETTE.primary,
  // "<CATEGORY_2>": PALETTE.secondary,
  // "<CATEGORY_3>": PALETTE.accent,
};

const state = { period: 12, category: ALL_CATEGORIES_LABEL };

let trendChart = null;
let breakdownChart = null;

// ---------- Theme ----------

function getCurrentTheme() {
  return document.documentElement.getAttribute('data-theme') || 'light';
}

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  document.getElementById('icon-sun').style.display = theme === 'dark' ? 'block' : 'none';
  document.getElementById('icon-moon').style.display = theme === 'dark' ? 'none' : 'block';
  try { localStorage.setItem(THEME_KEY, theme); } catch (e) {}

  if (trendChart && breakdownChart) {
    const isDark = theme === 'dark';
    const gridColor = isDark ? '#263248' : '#e2e8f0';
    trendChart.updateOptions({
      theme: { mode: theme },
      grid: { borderColor: gridColor },
      tooltip: { theme },
      colors: [isDark ? PALETTE.accent : PALETTE.primary],
    });
    breakdownChart.updateOptions({
      theme: { mode: theme },
      tooltip: { theme },
    });
  }
}

function initTheme() {
  applyTheme(getCurrentTheme());
  document.getElementById('theme-toggle').addEventListener('click', () => {
    applyTheme(getCurrentTheme() === 'dark' ? 'light' : 'dark');
  });
}

// ---------- Formatting / animation helpers ----------

function parseValue(str) {
  const m = String(str).match(/^([^0-9]*)([0-9,]*\.?[0-9]+)(.*)$/);
  if (!m) return { prefix: '', num: 0, suffix: String(str), decimals: 0, hasComma: false };
  const [, prefix, numStr, suffix] = m;
  return {
    prefix,
    num: parseFloat(numStr.replace(/,/g, '')),
    suffix,
    decimals: numStr.includes('.') ? numStr.split('.')[1].length : 0,
    hasComma: numStr.includes(','),
  };
}

function formatValue(num, parsed) {
  let numStr = parsed.decimals > 0 ? num.toFixed(parsed.decimals) : Math.round(num).toString();
  if (parsed.hasComma) {
    const parts = numStr.split('.');
    parts[0] = parseInt(parts[0], 10).toLocaleString('en-US');
    numStr = parts.join('.');
  }
  return parsed.prefix + numStr + parsed.suffix;
}

function animateKpiValue(el, targetStr) {
  const parsed = parseValue(targetStr);
  const start = parseFloat(el.dataset.rawNum || '0');
  const t0 = performance.now();
  const duration = 650;
  function frame(now) {
    const progress = Math.min((now - t0) / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    const current = start + (parsed.num - start) * eased;
    el.textContent = formatValue(current, parsed);
    if (progress < 1) {
      requestAnimationFrame(frame);
    } else {
      el.dataset.rawNum = String(parsed.num);
    }
  }
  requestAnimationFrame(frame);
}

function sparklineSvg(data, colorClass) {
  const w = 100, h = 28, pad = 3;
  const min = Math.min(...data), max = Math.max(...data);
  const range = (max - min) || 1;
  const points = data.map((v, i) => {
    const x = pad + (i / (data.length - 1)) * (w - pad * 2);
    const y = h - pad - ((v - min) / range) * (h - pad * 2);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');
  return `<svg viewBox="0 0 ${w} ${h}" class="kpi-spark" preserveAspectRatio="none">
    <polyline points="${points}" fill="none" class="${colorClass}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
  </svg>`;
}

// ---------- Data helpers ----------

function getTrendSeriesData() {
  const months = state.period;
  const startIdx = MONTHS.length - months;
  const categories = MONTHS.slice(startIdx);
  let data;
  if (state.category === ALL_CATEGORIES_LABEL) {
    data = categories.map((_, idx) => {
      const fullIdx = startIdx + idx;
      return BREAKDOWN_LABELS.reduce((sum, cat) => sum + MONTHLY_BY_CATEGORY[cat][fullIdx], 0);
    });
  } else {
    data = MONTHLY_BY_CATEGORY[state.category].slice(startIdx);
  }
  return { categories, data };
}

function computeBreakdownTotals(months) {
  const startIdx = MONTHS.length - months;
  return BREAKDOWN_LABELS.map(cat => {
    const arr = MONTHLY_BY_CATEGORY[cat].slice(startIdx);
    return Math.round(arr.reduce((a, b) => a + b, 0) * 10) / 10;
  });
}

function computeBreakdownColors() {
  if (state.category === ALL_CATEGORIES_LABEL) {
    return BREAKDOWN_LABELS.map(c => BREAKDOWN_COLOR_BY_CATEGORY[c]);
  }
  const muted = '#cbd5e1';
  return BREAKDOWN_LABELS.map(c => (c === state.category ? BREAKDOWN_COLOR_BY_CATEGORY[c] : muted));
}

// ---------- Rendering ----------

function renderBrand() {
  document.getElementById('brand-title').textContent = BRAND.name + ' — Demo Dashboard';
  document.getElementById('brand-subtitle').textContent = BRAND.subtitle;
  if (BRAND.logoUrl) {
    const chip = document.getElementById('logo-chip');
    const logo = document.getElementById('brand-logo');
    logo.src = BRAND.logoUrl;
    logo.alt = BRAND.name + ' logo';
    chip.style.display = 'flex';
  }
  const now = new Date();
  document.getElementById('last-updated').textContent =
    'Data refreshed ' + now.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function renderFilters() {
  const periodSelect = document.getElementById('filter-period');
  periodSelect.innerHTML = PERIODS.map(p => `<option value="${p.months}">${p.label}</option>`).join('');
  periodSelect.value = String(state.period);
  periodSelect.addEventListener('change', () => {
    state.period = parseInt(periodSelect.value, 10);
    updateDashboard();
  });

  const categorySelect = document.getElementById('filter-category');
  categorySelect.innerHTML = CATEGORIES.map(c => `<option value="${c}">${c}</option>`).join('');
  categorySelect.value = state.category;
  categorySelect.addEventListener('change', () => {
    state.category = categorySelect.value;
    updateDashboard();
  });
}

function renderKpis() {
  const grid = document.getElementById('kpi-grid');
  const data = KPI_DATA[state.category];
  grid.innerHTML = KPI_META.map((meta, i) => {
    const kpi = data[meta.key];
    const deltaClass = kpi.delta >= 0 ? 'kpi-delta-up' : 'kpi-delta-down';
    const sparkClass = kpi.delta >= 0 ? 'spark-up' : 'spark-down';
    return `
    <div class="kpi-card" style="animation-delay:${i * 60}ms">
      <div class="kpi-label">${meta.label}</div>
      <div class="kpi-value" id="kpi-value-${meta.key}" data-raw-num="0">${kpi.value}</div>
      <div class="${deltaClass}">${kpi.delta >= 0 ? '▲' : '▼'} ${Math.abs(kpi.delta)}%</div>
      ${sparklineSvg(kpi.spark, sparkClass)}
    </div>`;
  }).join('');

  KPI_META.forEach(meta => {
    const el = document.getElementById(`kpi-value-${meta.key}`);
    animateKpiValue(el, data[meta.key].value);
  });
}

function renderCharts() {
  const { categories, data } = getTrendSeriesData();
  const total = data.reduce((a, b) => a + b, 0);
  const avg = total / data.length;
  const isDark = getCurrentTheme() === 'dark';

  document.getElementById('trend-chart-title').textContent = "<TREND_CHART_TITLE>";
  document.getElementById('trend-chart-stat').textContent = `Total ${total.toFixed(1)} · Avg ${avg.toFixed(1)}/mo`;
  document.getElementById('breakdown-chart-title').textContent = "<BREAKDOWN_CHART_TITLE>";

  trendChart = new ApexCharts(document.querySelector('#trend-chart'), {
    chart: { type: 'area', height: 300, toolbar: { show: false }, fontFamily: 'Manrope, sans-serif' },
    theme: { mode: isDark ? 'dark' : 'light' },
    series: [{ name: "<TREND_SERIES_NAME>", data }],
    xaxis: { categories },
    colors: [isDark ? PALETTE.accent : PALETTE.primary],
    stroke: { curve: 'smooth', width: 3 },
    fill: { type: 'gradient', gradient: { opacityFrom: 0.35, opacityTo: 0 } },
    dataLabels: { enabled: false },
    grid: { borderColor: isDark ? '#263248' : '#e2e8f0' },
    tooltip: { theme: isDark ? 'dark' : 'light' },
  });
  trendChart.render();

  breakdownChart = new ApexCharts(document.querySelector('#breakdown-chart'), {
    chart: { type: 'donut', height: 300, fontFamily: 'Manrope, sans-serif' },
    theme: { mode: isDark ? 'dark' : 'light' },
    series: computeBreakdownTotals(state.period),
    labels: BREAKDOWN_LABELS,
    colors: computeBreakdownColors(),
    legend: { position: 'bottom' },
    dataLabels: { formatter: (val) => val.toFixed(0) + '%' },
    tooltip: { theme: isDark ? 'dark' : 'light' },
  });
  breakdownChart.render();
}

function updateTrendChart() {
  const { categories, data } = getTrendSeriesData();
  const total = data.reduce((a, b) => a + b, 0);
  const avg = total / data.length;
  document.getElementById('trend-chart-stat').textContent = `Total ${total.toFixed(1)} · Avg ${avg.toFixed(1)}/mo`;
  trendChart.updateOptions({ xaxis: { categories } });
  trendChart.updateSeries([{ name: "<TREND_SERIES_NAME>", data }]);
}

function updateBreakdownChart() {
  breakdownChart.updateOptions({ colors: computeBreakdownColors() });
  breakdownChart.updateSeries(computeBreakdownTotals(state.period));
}

function updateDashboard() {
  renderKpis();
  updateTrendChart();
  updateBreakdownChart();
}

function init() {
  try {
    renderBrand();
    initTheme();
    renderFilters();
    renderKpis();
    renderCharts();
    document.getElementById('loading').style.display = 'none';
    document.getElementById('app').style.display = 'block';
  } catch (err) {
    document.getElementById('loading').style.display = 'none';
    document.getElementById('error').textContent = 'Failed to render dashboard.';
    document.getElementById('error').style.display = 'block';
    console.error(err);
  }
}

init();
