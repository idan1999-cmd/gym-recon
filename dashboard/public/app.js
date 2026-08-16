/**
 * Ariel Fit & Spa / A+ Street Mall - Versatile Financial Dashboard
 * Supports: Cards View, Annual Trends & Charts View, Full 12-Month Matrix, and AI Insights.
 */

let currentMonth = 6;
let currentClub = 'all';
let currentView = 'cards';
let holidayMode = false;
let dashboardData = null;
let activeModalItem = null;

let chartMain = null;
let chartTrainer = null;
let chartPT = null;

const MONTH_NAMES = [
  'ינואר', 'פברואר', 'מרץ', 'אפריל', 'מאי', 'יוני',
  'יולי', 'אוגוסט', 'ספטמבר', 'אוקטובר', 'נובמבר', 'דצמבר'
];

function formatNIS(num) {
  if (num === undefined || num === null) return '₪ 0';
  const val = Math.round(num);
  return '₪ ' + val.toLocaleString('he-IL');
}

function showToast(msg) {
  const toast = document.getElementById('toast');
  const toastMsg = document.getElementById('toast-message');
  toastMsg.innerText = msg;
  toast.classList.remove('translate-y-20', 'opacity-0');
  setTimeout(() => {
    toast.classList.add('translate-y-20', 'opacity-0');
  }, 2500);
}

// View Switcher (Cards | Charts | Matrix)
function switchView(viewName) {
  currentView = viewName;

  document.querySelectorAll('.view-btn').forEach(btn => {
    btn.classList.remove('bg-blue-600', 'text-white', 'shadow-xs');
    btn.classList.add('text-blue-700', 'hover:bg-blue-100');
  });

  const activeBtn = document.getElementById(`view-${viewName}`);
  if (activeBtn) {
    activeBtn.classList.remove('text-blue-700', 'hover:bg-blue-100');
    activeBtn.classList.add('bg-blue-600', 'text-white', 'shadow-xs');
  }

  // Toggle View Containers
  document.getElementById('view-container-cards').classList.toggle('hidden', viewName !== 'cards');
  document.getElementById('view-container-charts').classList.toggle('hidden', viewName !== 'charts');
  document.getElementById('view-container-matrix').classList.toggle('hidden', viewName !== 'matrix');

  if (viewName === 'charts' && dashboardData) {
    renderAnnualCharts(dashboardData.annual_trends);
  }
}

function setClub(club) {
  currentClub = club;
  document.querySelectorAll('.club-tab-btn').forEach(btn => {
    btn.classList.remove('bg-slate-900', 'text-white', 'font-bold', 'shadow-xs');
    btn.classList.add('text-slate-600', 'hover:bg-slate-200');
  });

  const activeBtn = document.getElementById(`club-${club}`);
  if (activeBtn) {
    activeBtn.classList.remove('text-slate-600', 'hover:bg-slate-200');
    activeBtn.classList.add('bg-slate-900', 'text-white', 'font-bold', 'shadow-xs');
  }

  fetchDashboardData();
}

function navigateMonth(direction) {
  currentMonth += direction;
  if (currentMonth < 1) currentMonth = 1;
  if (currentMonth > 12) currentMonth = 12;
  
  document.getElementById('current-month-display').innerText = `${MONTH_NAMES[currentMonth - 1]} 2026`;
  fetchDashboardData();
}

function toggleHolidayMode() {
  holidayMode = !holidayMode;
  const btn = document.getElementById('holiday-toggle-btn');
  const text = document.getElementById('holiday-toggle-text');

  if (holidayMode) {
    btn.className = 'px-2.5 py-1.5 rounded-lg border text-xs font-bold transition flex items-center gap-1.5 bg-amber-500 border-amber-600 text-white shadow-xs';
    text.innerText = 'חודש חגים (15%-)';
    showToast('הופעל מקדם עונתיות לחודש חגים');
  } else {
    btn.className = 'px-2.5 py-1.5 rounded-lg border text-xs font-medium transition flex items-center gap-1.5 bg-white border-slate-200 text-slate-600 hover:bg-slate-50';
    text.innerText = 'חודש רגיל';
    showToast('חזרה לקצב עבודה רגיל');
  }

  fetchDashboardData();
}

function toggleFixedSection() {
  const content = document.getElementById('fixed-section-content');
  const icon = document.getElementById('fixed-chevron-icon');
  const isHidden = content.classList.contains('hidden');

  if (isHidden) {
    content.classList.remove('hidden');
    icon.classList.add('rotate-180');
  } else {
    content.classList.add('hidden');
    icon.classList.remove('rotate-180');
  }
}

async function syncData() {
  const icons = document.querySelectorAll('.sync-icon');
  icons.forEach(i => i.classList.add('animate-spin'));
  
  try {
    const res = await fetch('/api/sync', { method: 'POST' });
    const data = await res.json();
    showToast(data.message || 'הנתונים סונכרנו בהצלחה!');
    await fetchDashboardData();
  } catch (err) {
    showToast('שגיאה בסנכרון נתונים');
  } finally {
    icons.forEach(i => i.classList.remove('animate-spin'));
  }
}

async function fetchDashboardData() {
  try {
    const res = await fetch(`/api/data?month=${currentMonth}&club=${currentClub}&holiday=${holidayMode}`);
    dashboardData = await res.json();
    renderDashboard(dashboardData);
  } catch (err) {
    console.error('Error loading dashboard data:', err);
  }
}

function renderDashboard(data) {
  if (!data) return;

  const sum = data.summary;
  const meta = data.metadata;

  document.getElementById('current-month-display').innerText = `${meta.month_name} ${meta.year}`;

  // Top KPIs
  document.getElementById('strip-rev-actual').innerText = formatNIS(sum.total_revenue.actual);
  document.getElementById('strip-rev-budget').innerText = formatNIS(sum.total_revenue.budget);
  document.getElementById('strip-rev-pct').innerText = `${sum.total_revenue.pct}%`;
  document.getElementById('strip-rev-proj').innerText = formatNIS(sum.total_revenue.projected);

  document.getElementById('strip-exp-actual').innerText = formatNIS(sum.total_expenses.actual);
  document.getElementById('strip-exp-budget').innerText = formatNIS(sum.total_expenses.budget);
  document.getElementById('strip-exp-pct').innerText = `${sum.total_expenses.pct}%`;
  document.getElementById('strip-exp-proj').innerText = formatNIS(sum.total_expenses.projected);

  // 1. Render AI Smart Insights
  renderSmartInsights(data.smart_insights);

  // 2. Render Cards View (View 1)
  renderCategoryCards(data.incomes, 'incomes-cards-container', 'income');
  renderCategoryCards(data.variable_expenses, 'expenses-cards-container', 'expense');
  renderFixedCards(data.fixed_expenses);

  // 3. Render Charts View (View 2)
  if (currentView === 'charts') {
    renderAnnualCharts(data.annual_trends);
  }

  // 4. Render Matrix View (View 3)
  renderFinancialMatrix(data.incomes, data.variable_expenses, data.fixed_expenses);

  lucide.createIcons();
}

function renderSmartInsights(tips) {
  const container = document.getElementById('smart-insights-section');
  if (!tips || tips.length === 0) {
    container.innerHTML = '';
    return;
  }

  container.innerHTML = `
    <div class="p-3.5 bg-gradient-to-r from-blue-50 to-indigo-50/60 rounded-2xl border border-blue-100 shadow-2xs space-y-2">
      <div class="flex items-center justify-between">
        <span class="text-xs font-bold text-blue-950 flex items-center gap-1.5">
          <i data-lucide="sparkles" class="w-4 h-4 text-blue-600"></i>
          תובנות חכמות וניתוח שינויים (AI Pulse)
        </span>
        <span class="text-[10px] bg-blue-600 text-white font-bold px-2 py-0.5 rounded-full">חי</span>
      </div>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1">
        ${tips.map(t => `
          <div class="p-2.5 bg-white/90 rounded-xl border border-blue-100/80 flex items-start gap-2.5 text-xs shadow-2xs">
            <i data-lucide="${t.icon}" class="w-4 h-4 text-blue-600 mt-0.5 flex-shrink-0"></i>
            <div>
              <strong class="font-bold text-slate-800 block">${t.title}</strong>
              <p class="text-slate-500 mt-0.5 text-[11px] leading-relaxed">${t.text}</p>
            </div>
          </div>
        `).join('')}
      </div>
    </div>
  `;
}

function renderCategoryCards(items, containerId, type) {
  const container = document.getElementById(containerId);
  container.innerHTML = '';

  if (!items || items.length === 0) {
    container.innerHTML = '<div class="text-xs text-slate-400 p-4 text-center">אין נתונים לחודש זה</div>';
    return;
  }

  items.forEach((item, idx) => {
    const isIncome = type === 'income';
    const b = item.budget;
    const a = item.actual;
    const pct = b > 0 ? Math.min((a / b) * 100, 100) : 0;
    
    let statusHTML = '';
    if (isIncome) {
      if (a >= b && b > 0) {
        statusHTML = `<span class="text-xs font-bold text-emerald-600 flex items-center gap-1">
          <i data-lucide="check-circle" class="w-3.5 h-3.5"></i>
          עמידה ביעד בתוספת ₪${Math.round(a - b).toLocaleString('he-IL')}
        </span>`;
      } else {
        statusHTML = `<span class="text-xs font-medium text-slate-500">נשאר לגבות ₪${Math.max(Math.round(b - a), 0).toLocaleString('he-IL')}</span>`;
      }
    } else {
      if (a > b && b > 0) {
        statusHTML = `<span class="text-xs font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded-full flex items-center gap-1">
          <span class="w-4 h-4 rounded-full bg-blue-600 text-white flex items-center justify-center text-[10px] font-black">!</span>
          חריגה של ₪${Math.round(a - b).toLocaleString('he-IL')}
        </span>`;
      } else {
        statusHTML = `<span class="text-xs font-medium text-slate-500">נשאר להוציא ₪${Math.max(Math.round(b - a), 0).toLocaleString('he-IL')}</span>`;
      }
    }

    const card = document.createElement('div');
    card.className = 'app-card p-4 sm:p-5 flex flex-col justify-between cursor-pointer';
    card.onclick = (e) => {
      if (e.target.closest('.tx-drawer-btn') || e.target.closest('.tx-drawer-box')) return;
      openDrilldownModal(item);
    };

    const itemId = `card-tx-${type}-${idx}`;

    card.innerHTML = `
      <div>
        <div class="flex items-center justify-between mb-3">
          <div class="flex items-center gap-2">
            <h3 class="text-base font-black text-slate-900">${item.name}</h3>
            ${item.club ? `<span class="text-[10px] font-semibold px-2 py-0.5 bg-slate-100 text-slate-600 rounded-md">${item.club}</span>` : ''}
          </div>
          <button class="text-slate-400 hover:text-slate-700 p-1">
            <i data-lucide="more-vertical" class="w-4 h-4"></i>
          </button>
        </div>

        <div class="flex items-baseline justify-between mb-2">
          <div>
            <span class="text-[11px] text-slate-400 block">${isIncome ? 'צפוי להכנס' : 'צפוי לצאת / יעד'}</span>
            <span class="text-sm font-bold text-slate-700">${formatNIS(b)}</span>
          </div>
          <div class="text-left">
            <span class="text-[11px] text-slate-400 block">${isIncome ? 'נכנס בפועל' : 'יצא בפועל'}</span>
            <span class="text-lg font-black text-blue-600">${formatNIS(a)}</span>
          </div>
        </div>

        <div class="w-full bg-slate-100 h-2.5 rounded-full overflow-hidden mb-2.5">
          <div class="bg-blue-600 h-full rounded-full transition-all duration-500" style="width: ${pct}%"></div>
        </div>

        <div class="flex items-center justify-between pt-1">
          <div>${statusHTML}</div>
          <button onclick="toggleCardTransactions('${itemId}')" class="tx-drawer-btn text-xs font-semibold text-slate-400 hover:text-slate-700 flex items-center gap-1 transition">
            <span>פירוט חודשי</span>
            <i data-lucide="chevron-down" id="icon-${itemId}" class="w-3.5 h-3.5 transition-transform"></i>
          </button>
        </div>
      </div>

      <div id="${itemId}" class="tx-drawer-box hidden mt-3 pt-3 border-t border-slate-100 space-y-1.5">
        ${renderCardTransactionsList(item.transactions)}
      </div>
    `;

    container.appendChild(card);
  });
}

function renderCardTransactionsList(txs) {
  if (!txs || txs.length === 0) {
    return '<div class="text-[11px] text-slate-400 py-1">אין פירוט עסקאות לחודש זה</div>';
  }
  return txs.map(t => `
    <div class="flex items-center justify-between text-xs py-1 px-2 rounded-lg bg-slate-50 border border-slate-100">
      <div class="flex items-center gap-2 text-slate-700">
        <span class="text-[10px] text-slate-400 font-mono">${t.date}</span>
        <span class="font-medium">${t.desc}</span>
      </div>
      <span class="font-bold text-slate-900">${formatNIS(t.amount)}</span>
    </div>
  `).join('');
}

function toggleCardTransactions(boxId) {
  const box = document.getElementById(boxId);
  const icon = document.getElementById(`icon-${boxId}`);
  if (!box) return;

  const isHidden = box.classList.contains('hidden');
  if (isHidden) {
    box.classList.remove('hidden');
    if (icon) icon.classList.add('rotate-180');
  } else {
    box.classList.add('hidden');
    if (icon) icon.classList.remove('rotate-180');
  }
}

function renderFixedCards(fixedItems) {
  const container = document.getElementById('fixed-cards-container');
  let totalFixed = 0;
  container.innerHTML = '';

  fixedItems.forEach(item => {
    totalFixed += item.actual;
    const card = document.createElement('div');
    card.className = 'p-3 bg-white rounded-xl border border-slate-200 flex items-center justify-between text-xs hover:border-slate-300 transition cursor-pointer';
    card.onclick = () => openDrilldownModal(item);
    
    card.innerHTML = `
      <div>
        <span class="font-bold text-slate-800">${item.name}</span>
        <span class="text-[10px] text-slate-400 mr-2">קבוע בחוזה</span>
      </div>
      <div class="flex items-center gap-4">
        <span class="text-slate-500">תקציב: ${formatNIS(item.budget)}</span>
        <span class="font-bold text-slate-900">${formatNIS(item.actual)}</span>
      </div>
    `;
    container.appendChild(card);
  });

  document.getElementById('fixed-total-header').innerText = formatNIS(totalFixed);
}

// =========================================================================
// ANNUAL CHARTS & TRENDS (VIEW 2)
// =========================================================================
function renderAnnualCharts(trends) {
  if (!trends) return;

  // Chart 1: Revenue vs Expenses Full Year
  const mainOpts = {
    series: [
      { name: 'הכנסות בפועל', data: trends.revenue.actual },
      { name: 'הוצאות בפועל', data: trends.expenses.actual },
      { name: 'רווח תפעולי', data: trends.profit }
    ],
    chart: {
      type: 'bar',
      height: 280,
      fontFamily: 'Heebo, sans-serif',
      toolbar: { show: false }
    },
    colors: ['#16a34a', '#dc2626', '#2563eb'],
    plotOptions: {
      bar: { horizontal: false, columnWidth: '55%', borderRadius: 4 }
    },
    dataLabels: { enabled: false },
    stroke: { show: true, width: 2, colors: ['transparent'] },
    xaxis: { categories: trends.months_labels },
    yaxis: {
      labels: { formatter: (val) => '₪' + (val / 1000).toFixed(0) + 'k' }
    },
    tooltip: { y: { formatter: (val) => formatNIS(val) } }
  };

  if (chartMain) chartMain.updateOptions(mainOpts);
  else {
    chartMain = new ApexCharts(document.querySelector("#annual-main-chart"), mainOpts);
    chartMain.render();
  }

  // Chart 2: Trainer Labor Trend
  const trainerOpts = {
    series: [{ name: 'עלות שכר מאמנים והדרכה', data: trends.trainers }],
    chart: { type: 'area', height: 240, fontFamily: 'Heebo, sans-serif', toolbar: { show: false } },
    colors: ['#9333ea'],
    dataLabels: { enabled: false },
    stroke: { curve: 'smooth', width: 3 },
    fill: { type: 'gradient', gradient: { opacityFrom: 0.5, opacityTo: 0.05 } },
    xaxis: { categories: trends.months_labels },
    yaxis: { labels: { formatter: (val) => '₪' + (val / 1000).toFixed(0) + 'k' } },
    tooltip: { y: { formatter: (val) => formatNIS(val) } }
  };

  if (chartTrainer) chartTrainer.updateOptions(trainerOpts);
  else {
    chartTrainer = new ApexCharts(document.querySelector("#trainer-trend-chart"), trainerOpts);
    chartTrainer.render();
  }

  // Chart 3: PT Profitability Trend
  const ptOpts = {
    series: [
      { name: 'הכנסות אישיים', data: trends.pt.revenue },
      { name: 'עלות מאמנים אישיים', data: trends.pt.cost }
    ],
    chart: { type: 'line', height: 240, fontFamily: 'Heebo, sans-serif', toolbar: { show: false } },
    colors: ['#059669', '#e11d48'],
    stroke: { width: [3, 3], curve: 'straight' },
    xaxis: { categories: trends.months_labels },
    yaxis: { labels: { formatter: (val) => '₪' + (val / 1000).toFixed(0) + 'k' } },
    tooltip: { y: { formatter: (val) => formatNIS(val) } }
  };

  if (chartPT) chartPT.updateOptions(ptOpts);
  else {
    chartPT = new ApexCharts(document.querySelector("#pt-trend-chart"), ptOpts);
    chartPT.render();
  }
}

// =========================================================================
// FULL FINANCIAL MATRIX (VIEW 3)
// =========================================================================
function renderFinancialMatrix(incomes, varExp, fixExp) {
  const tbody = document.getElementById('matrix-tbody');
  if (!tbody) return;
  tbody.innerHTML = '';

  const allItems = [
    ...incomes.map(x => ({ ...x, group: 'הכנסה', groupClass: 'text-emerald-700 bg-emerald-50' })),
    ...varExp.map(x => ({ ...x, group: 'משתנה', groupClass: 'text-blue-700 bg-blue-50' })),
    ...fixExp.map(x => ({ ...x, group: 'קבוע', groupClass: 'text-slate-700 bg-slate-100' }))
  ];

  tbody.innerHTML = allItems.map(item => {
    const months = item.all_months || {};
    return `
      <tr class="hover:bg-slate-50 transition cursor-pointer" onclick='openDrilldownModal(${JSON.stringify(item)})'>
        <td class="py-2.5 px-3 font-bold text-slate-900">${item.name}</td>
        <td class="py-2.5 px-2"><span class="px-2 py-0.5 rounded text-[10px] font-bold ${item.groupClass}">${item.group}</span></td>
        <td class="py-2.5 px-2 font-medium text-slate-500">${formatNIS(item.budget)}</td>
        <td class="py-2.5 px-2">${formatNIS(months[1]?.actual || 0)}</td>
        <td class="py-2.5 px-2">${formatNIS(months[2]?.actual || 0)}</td>
        <td class="py-2.5 px-2">${formatNIS(months[3]?.actual || 0)}</td>
        <td class="py-2.5 px-2">${formatNIS(months[4]?.actual || 0)}</td>
        <td class="py-2.5 px-2">${formatNIS(months[5]?.actual || 0)}</td>
        <td class="py-2.5 px-2 bg-blue-50/60 font-bold text-blue-700">${formatNIS(months[6]?.actual || 0)}</td>
        <td class="py-2.5 px-2 text-slate-400">${formatNIS(months[7]?.actual || 0)}</td>
      </tr>
    `;
  }).join('');
}

// =========================================================================
// MODAL DRILLDOWN (EXACT MATCH TO IMAGE 2)
// =========================================================================
function openDrilldownModal(item) {
  activeModalItem = item;

  document.getElementById('modal-category-title').innerText = `${item.name} לפי חודשים`;
  document.getElementById('modal-club-badge').innerText = item.club || 'כל המועדון';
  document.getElementById('modal-month-name').innerText = dashboardData.metadata.month_name;
  document.getElementById('modal-target-amount').innerText = formatNIS(item.budget);
  document.getElementById('modal-forecast-amount').innerText = `תחזית חכמה לסוף חודש: ${formatNIS(item.projected)} (מבוסס קצב יומי)`;
  document.getElementById('modal-explanation-text').innerText = item.explanation || 'סעיף תקציבי שוטף מתוך פעילות המועדון.';

  render5MonthBars(item.history.history_bars, item.budget);

  const txContainer = document.getElementById('modal-transactions-list');
  txContainer.innerHTML = renderCardTransactionsList(item.transactions);

  document.getElementById('target-editor-box').classList.add('hidden');
  document.getElementById('target-edit-input').value = Math.round(item.budget);

  const modal = document.getElementById('drilldown-modal');
  const card = document.getElementById('modal-card');
  modal.classList.remove('hidden');
  setTimeout(() => {
    modal.classList.remove('opacity-0');
    card.classList.remove('scale-95');
    card.classList.add('scale-100');
  }, 10);

  lucide.createIcons();
}

function render5MonthBars(historyBars, targetVal) {
  const container = document.getElementById('modal-bars-container');
  container.innerHTML = '';

  if (!historyBars || historyBars.length === 0) return;

  const maxVal = Math.max(...historyBars.map(b => Math.max(b.actual, b.budget)), targetVal, 100);

  historyBars.forEach(bar => {
    const isCurrent = bar.is_current;
    const actualHeightPct = Math.max((bar.actual / maxVal) * 100, 10);
    const targetHeightPct = Math.max((bar.budget / maxVal) * 100, 10);

    const col = document.createElement('div');
    col.className = 'flex-1 flex flex-col items-center justify-end h-full group relative';

    if (isCurrent) {
      col.innerHTML = `
        <span class="text-[11px] font-black text-slate-900 mb-1">${Math.round(bar.budget).toLocaleString('he-IL')}</span>
        <div class="w-8 rounded-full border-2 border-blue-600 p-0.5 flex flex-col justify-end bg-blue-50/50" style="height: ${targetHeightPct}%">
          <div class="w-full bg-blue-600 rounded-full transition-all duration-500" style="height: ${Math.min((bar.actual / Math.max(bar.budget, 1)) * 100, 100)}%"></div>
        </div>
        <span class="text-xs font-black text-blue-600 mt-2">${bar.short_name}</span>
      `;
    } else {
      col.innerHTML = `
        <span class="text-[10px] font-bold text-slate-600 mb-1">${Math.round(bar.actual).toLocaleString('he-IL')}</span>
        <div class="w-8 rounded-full bg-blue-100 hover:bg-blue-200 transition-all" style="height: ${actualHeightPct}%"></div>
        <span class="text-xs font-medium text-slate-400 mt-2">${bar.short_name}</span>
      `;
    }

    container.appendChild(col);
  });
}

function closeModal() {
  const modal = document.getElementById('drilldown-modal');
  const card = document.getElementById('modal-card');
  modal.classList.add('opacity-0');
  card.classList.remove('scale-100');
  card.classList.add('scale-95');
  setTimeout(() => {
    modal.classList.add('hidden');
    activeModalItem = null;
  }, 200);
}

function toggleExplanation() {
  const text = document.getElementById('modal-explanation-text');
  const icon = document.getElementById('explanation-chevron');
  const isHidden = text.classList.contains('hidden');

  if (isHidden) {
    text.classList.remove('hidden');
    icon.classList.add('rotate-180');
  } else {
    text.classList.add('hidden');
    icon.classList.remove('rotate-180');
  }
}

function openTargetEditor() {
  const editor = document.getElementById('target-editor-box');
  editor.classList.toggle('hidden');
}

async function saveNewTarget() {
  if (!activeModalItem) return;
  const inputVal = parseFloat(document.getElementById('target-edit-input').value);
  if (isNaN(inputVal) || inputVal < 0) {
    showToast('נא להזין סכום תקין');
    return;
  }

  try {
    const res = await fetch('/api/target', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        club: activeModalItem.club || 'חדר כושר',
        code: activeModalItem.code || '',
        month: currentMonth,
        target: inputVal
      })
    });

    const data = await res.json();
    if (data.success) {
      showToast('היעד עודכן ונשמר בהצלחה!');
      document.getElementById('modal-target-amount').innerText = formatNIS(inputVal);
      document.getElementById('target-editor-box').classList.add('hidden');
      await fetchDashboardData();
      if (activeModalItem) {
        activeModalItem.budget = inputVal;
        render5MonthBars(activeModalItem.history.history_bars, inputVal);
      }
    }
  } catch (err) {
    showToast('שגיאה בשמירת היעד');
  }
}

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') closeModal();
});

document.getElementById('drilldown-modal').addEventListener('click', (e) => {
  if (e.target.id === 'drilldown-modal') closeModal();
});

document.addEventListener('DOMContentLoaded', () => {
  fetchDashboardData();
});
