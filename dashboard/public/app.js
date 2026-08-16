/**
 * Ariel Fit & Spa - Dashboard Frontend Logic
 */

let currentMonth = 6;
let currentClub = 'all';
let dashboardData = null;
let revenueChart = null;

// Format Shekels
function formatNIS(num) {
  if (num === undefined || num === null) return '₪0';
  return '₪' + Math.round(num).toLocaleString('he-IL');
}

function formatPct(pct) {
  if (pct === undefined || pct === null) return '0%';
  return pct.toFixed(1) + '%';
}

// Show Toast
function showToast(message) {
  const toast = document.getElementById('toast');
  const toastMsg = document.getElementById('toast-message');
  toastMsg.innerText = message;
  toast.classList.remove('translate-y-20', 'opacity-0');
  setTimeout(() => {
    toast.classList.add('translate-y-20', 'opacity-0');
  }, 3000);
}

// Set Club Filter
function setClub(club) {
  currentClub = club;
  
  // Update Buttons UI
  document.querySelectorAll('.club-toggle-btn').forEach(btn => {
    btn.classList.remove('bg-emerald-600', 'text-white', 'font-semibold', 'shadow-sm');
    btn.classList.add('text-slate-400');
  });

  const activeBtn = document.getElementById(`club-${club}`);
  if (activeBtn) {
    activeBtn.classList.remove('text-slate-400');
    activeBtn.classList.add('bg-emerald-600', 'text-white', 'font-semibold', 'shadow-sm');
  }

  fetchDashboardData();
}

// Change Month
function changeMonth(month) {
  currentMonth = parseInt(month, 10);
  fetchDashboardData();
}

// Toggle Fixed Expenses Drawer
function toggleFixedExpenses() {
  const drawer = document.getElementById('fixed-expenses-drawer');
  const chevron = document.getElementById('fixed-chevron');
  const isHidden = drawer.classList.contains('hidden');
  
  if (isHidden) {
    drawer.classList.remove('hidden');
    chevron.classList.add('rotate-180');
  } else {
    drawer.classList.add('hidden');
    chevron.classList.remove('rotate-180');
  }
}

// Sync Data with Backend
async function syncData() {
  const syncIcons = document.querySelectorAll('.sync-icon');
  syncIcons.forEach(i => i.classList.add('animate-spin'));
  
  try {
    const res = await fetch('/api/sync', { method: 'POST' });
    const data = await res.json();
    showToast(data.message || 'הסנכרון הושלם בהצלחה!');
    await fetchDashboardData();
  } catch (err) {
    console.error('Sync failed:', err);
    showToast('שגיאה בסנכרון נתונים');
  } finally {
    syncIcons.forEach(i => i.classList.remove('animate-spin'));
  }
}

// Fetch Data from Backend API
async function fetchDashboardData() {
  try {
    const res = await fetch(`/api/data?month=${currentMonth}&club=${currentClub}`);
    dashboardData = await res.json();
    renderDashboard(dashboardData);
  } catch (err) {
    console.error('Error fetching dashboard data:', err);
  }
}

// Render Dashboard
function renderDashboard(data) {
  if (!data) return;

  const kpis = data.kpis;
  const meta = data.metadata;

  // 1. Update Sync timestamp
  document.getElementById('sync-timestamp').innerText = `סנכרון אחרון: ${meta.last_synced}`;

  // 2. Render Smart Alerts
  renderAlerts(data.alerts);

  // 3. Render Top KPI Cards
  // Revenue Card
  document.getElementById('kpi-rev-actual').innerText = formatNIS(kpis.total_revenue.actual);
  document.getElementById('kpi-rev-budget').innerText = formatNIS(kpis.total_revenue.budget);
  document.getElementById('kpi-rev-pct').innerText = formatPct(kpis.total_revenue.pct);
  document.getElementById('kpi-rev-bar').style.width = `${Math.min(kpis.total_revenue.pct, 100)}%`;
  document.getElementById('kpi-cash-collected').innerText = formatNIS(kpis.total_revenue.cash_collected);
  document.getElementById('kpi-credit-next-month').innerText = formatNIS(kpis.total_revenue.credit_next_month);

  // Expenses Card
  document.getElementById('kpi-exp-actual').innerText = formatNIS(kpis.total_expenses.actual);
  document.getElementById('kpi-exp-budget').innerText = formatNIS(kpis.total_expenses.budget);
  document.getElementById('kpi-exp-pct').innerText = formatPct(kpis.total_expenses.pct);
  document.getElementById('kpi-exp-bar').style.width = `${Math.min(kpis.total_expenses.pct, 100)}%`;
  document.getElementById('kpi-exp-projected').innerText = formatNIS(kpis.total_expenses.projected);

  // Trainers Labor Card
  document.getElementById('kpi-trainers-actual').innerText = formatNIS(kpis.trainers_labor.actual);
  document.getElementById('kpi-trainers-budget').innerText = formatNIS(kpis.trainers_labor.budget);
  document.getElementById('kpi-trainers-pct-rev').innerText = formatPct(kpis.trainers_labor.pct_of_rev);
  const trainerPct = (kpis.trainers_labor.actual / Math.max(kpis.trainers_labor.budget, 1)) * 100;
  document.getElementById('kpi-trainers-bar').style.width = `${Math.min(trainerPct, 100)}%`;
  
  const trainerStatusBadge = document.getElementById('kpi-trainers-status');
  if (kpis.trainers_labor.is_over_budget) {
    trainerStatusBadge.innerText = 'חריגה מתקציב';
    trainerStatusBadge.className = 'text-rose-400 font-bold px-1.5 py-0.5 bg-rose-500/10 rounded text-[11px]';
  } else {
    trainerStatusBadge.innerText = 'בתקציב';
    trainerStatusBadge.className = 'text-emerald-400 font-bold px-1.5 py-0.5 bg-emerald-500/10 rounded text-[11px]';
  }

  // PT Profitability Card
  document.getElementById('kpi-pt-revenue').innerText = formatNIS(kpis.personal_training.revenue);
  document.getElementById('kpi-pt-cost').innerText = formatNIS(kpis.personal_training.cost);
  document.getElementById('kpi-pt-profit').innerText = (kpis.personal_training.profit >= 0 ? '+' : '') + formatNIS(kpis.personal_training.profit);
  document.getElementById('kpi-pt-margin').innerText = `${kpis.personal_training.margin_pct}% מתח`;
  document.getElementById('kpi-pt-bar').style.width = `${Math.min(Math.max(kpis.personal_training.margin_pct, 0), 100)}%`;

  // Net Operational Profit
  const netAct = kpis.net_profit.actual;
  const netBud = kpis.net_profit.budget;
  document.getElementById('kpi-net-actual').innerText = formatNIS(netAct);
  document.getElementById('kpi-net-budget').innerText = formatNIS(netBud);
  const netVar = netAct - netBud;
  const netVarEl = document.getElementById('kpi-net-variance');
  netVarEl.innerText = (netVar >= 0 ? '+' : '') + formatNIS(netVar);
  netVarEl.className = netVar >= 0 ? 'font-bold text-emerald-400' : 'font-bold text-amber-400';

  // 4. Render Revenue Target Categories
  renderRevenueCategories(data.revenue_categories);

  // 5. Render Chart
  renderChart(data.revenue_categories);

  // 6. Render Trainer Hours List
  renderTrainers(data.trainers, kpis.trainers_labor.budget);

  // 7. Render Variable Expenses Table
  renderVariableExpenses(data.variable_expenses);

  // 8. Render Fixed Expenses Drawer
  renderFixedExpenses(data.fixed_expenses);

  // Re-initialize Lucide Icons
  lucide.createIcons();
}

function renderAlerts(alerts) {
  const container = document.getElementById('alerts-container');
  if (!alerts || alerts.length === 0) {
    container.innerHTML = '';
    return;
  }

  container.innerHTML = alerts.map(a => {
    let bg = 'bg-slate-800/80 border-slate-700 text-slate-200';
    let icon = 'alert-circle';
    let iconColor = 'text-amber-400';

    if (a.type === 'danger') {
      bg = 'bg-rose-950/40 border-rose-800/50 text-rose-200';
      icon = 'alert-triangle';
      iconColor = 'text-rose-400';
    } else if (a.type === 'success') {
      bg = 'bg-emerald-950/40 border-emerald-800/50 text-emerald-200';
      icon = 'check-circle-2';
      iconColor = 'text-emerald-400';
    } else if (a.type === 'warning') {
      bg = 'bg-amber-950/40 border-amber-800/50 text-amber-200';
      icon = 'bell-ring';
      iconColor = 'text-amber-400';
    }

    return `
      <div class="p-3.5 rounded-xl border ${bg} flex items-center justify-between gap-3 text-xs shadow-sm">
        <div class="flex items-center gap-3">
          <i data-lucide="${icon}" class="w-4 h-4 ${iconColor} flex-shrink-0"></i>
          <div>
            <span class="font-bold ml-1.5">${a.title}:</span>
            <span class="opacity-90">${a.message}</span>
          </div>
        </div>
        <span class="text-[11px] font-semibold px-2 py-0.5 rounded bg-white/10 whitespace-nowrap">${a.action}</span>
      </div>
    `;
  }).join('');
}

function renderRevenueCategories(categories) {
  const grid = document.getElementById('revenue-categories-grid');
  grid.innerHTML = '';

  const icons = {
    memberships: { icon: 'credit-card', color: 'text-emerald-400' },
    personal_training: { icon: 'user-check', color: 'text-cyan-400' },
    punch_cards: { icon: 'ticket', color: 'text-purple-400' },
    registration: { icon: 'user-plus', color: 'text-amber-400' },
    other_income: { icon: 'layers', color: 'text-blue-400' }
  };

  for (const [key, item] of Object.entries(categories)) {
    const pct = item.budget > 0 ? (item.actual / item.budget) * 100 : 100;
    const isSuccess = pct >= 90;
    const iconInfo = icons[key] || { icon: 'dollar-sign', color: 'text-slate-400' };

    const card = document.createElement('div');
    card.className = 'glass-card rounded-xl p-4 hover:border-slate-700 transition flex flex-col justify-between';
    card.innerHTML = `
      <div>
        <div class="flex items-center justify-between text-xs mb-2">
          <span class="font-semibold text-slate-300 flex items-center gap-1.5">
            <i data-lucide="${iconInfo.icon}" class="w-3.5 h-3.5 ${iconInfo.color}"></i>
            ${item.name}
          </span>
          <span class="text-[11px] font-bold ${isSuccess ? 'text-emerald-400 bg-emerald-500/10' : 'text-amber-400 bg-amber-500/10'} px-1.5 py-0.5 rounded">
            ${pct.toFixed(0)}% עמידה
          </span>
        </div>
        <div class="text-xl font-bold text-white mb-1">${formatNIS(item.actual)}</div>
        <div class="text-[11px] text-slate-400">יעד תקציב: <span class="text-slate-300 font-semibold">${formatNIS(item.budget)}</span></div>
      </div>
      
      <div class="w-full bg-slate-800 h-1.5 rounded-full mt-3 overflow-hidden">
        <div class="${isSuccess ? 'bg-emerald-500' : 'bg-amber-500'} h-full rounded-full transition-all duration-500" style="width: ${Math.min(pct, 100)}%"></div>
      </div>
    `;
    grid.appendChild(card);
  }
}

function renderChart(categories) {
  const names = [];
  const actuals = [];
  const budgets = [];

  for (const [key, item] of Object.entries(categories)) {
    names.push(item.name);
    actuals.push(Math.round(item.actual));
    budgets.push(Math.round(item.budget));
  }

  const options = {
    series: [
      { name: 'ביצוע בפועל', data: actuals },
      { name: 'יעד תקציבי', data: budgets }
    ],
    chart: {
      type: 'bar',
      height: 310,
      fontFamily: 'Heebo, sans-serif',
      toolbar: { show: false },
      background: 'transparent'
    },
    colors: ['#22c55e', '#64748b'],
    plotOptions: {
      bar: {
        horizontal: false,
        columnWidth: '45%',
        borderRadius: 4
      }
    },
    dataLabels: { enabled: false },
    stroke: { show: true, width: 2, colors: ['transparent'] },
    xaxis: {
      categories: names,
      labels: {
        style: { colors: '#94a3b8', fontSize: '11px' }
      },
      axisBorder: { color: '#334155' },
      axisTicks: { color: '#334155' }
    },
    yaxis: {
      labels: {
        formatter: (val) => '₪' + (val / 1000).toFixed(0) + 'k',
        style: { colors: '#94a3b8', fontSize: '11px' }
      }
    },
    legend: {
      position: 'top',
      horizontalAlign: 'left',
      labels: { colors: '#cbd5e1' }
    },
    grid: {
      borderColor: '#334155',
      strokeDashArray: 3
    },
    tooltip: {
      theme: 'dark',
      y: { formatter: (val) => formatNIS(val) }
    }
  };

  if (revenueChart) {
    revenueChart.updateOptions(options);
  } else {
    revenueChart = new ApexCharts(document.querySelector("#revenue-chart"), options);
    revenueChart.render();
  }
}

function renderTrainers(trainers, totalBudget) {
  const container = document.getElementById('trainers-list');
  document.getElementById('trainers-total-footer').innerText = formatNIS(totalBudget);

  if (!trainers || trainers.length === 0) {
    container.innerHTML = '<div class="text-xs text-slate-500 py-4 text-center">אין שעות מאמנים לתצוגה בחודש זה</div>';
    return;
  }

  container.innerHTML = trainers.map(t => `
    <div class="p-2.5 rounded-xl bg-slate-900/60 border border-slate-800 flex items-center justify-between hover:border-slate-700 transition">
      <div>
        <div class="font-bold text-xs text-slate-200">${t.name}</div>
        <div class="text-[11px] text-slate-400 flex items-center gap-2 mt-0.5">
          <span class="px-1.5 py-0.2 bg-slate-800 text-slate-300 rounded text-[10px]">${t.category}</span>
          ${t.hours > 0 ? `<span>${t.hours.toFixed(1)} שעות</span>` : ''}
        </div>
      </div>
      <div class="text-left font-bold text-xs text-purple-300">${formatNIS(t.amount)}</div>
    </div>
  `).join('');
}

function renderVariableExpenses(expenses) {
  const tbody = document.getElementById('variable-expenses-tbody');
  if (!expenses || expenses.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-slate-500">אין סעיפי הוצאה</td></tr>';
    return;
  }

  tbody.innerHTML = expenses.map(item => {
    const pct = item.budget > 0 ? (item.actual / item.budget) * 100 : 0;
    const isOver = item.actual > item.budget;
    const diff = item.actual - item.budget;

    return `
      <tr class="hover:bg-slate-800/30 transition text-slate-300">
        <td class="py-2.5 pr-2 font-medium text-white">${item.name}</td>
        <td class="py-2.5 text-slate-400">${item.category}</td>
        <td class="py-2.5">${formatNIS(item.budget)}</td>
        <td class="py-2.5 font-bold ${isOver ? 'text-rose-400' : 'text-slate-200'}">${formatNIS(item.actual)}</td>
        <td class="py-2.5 ${diff > 0 ? 'text-rose-400' : 'text-emerald-400'} font-semibold">
          ${diff > 0 ? '+' : ''}${formatNIS(diff)}
        </td>
        <td class="py-2.5 pl-2">
          <span class="px-2 py-0.5 rounded text-[11px] font-bold ${isOver ? 'bg-rose-500/10 text-rose-400' : 'bg-emerald-500/10 text-emerald-400'}">
            ${pct.toFixed(0)}%
          </span>
        </td>
      </tr>
    `;
  }).join('');
}

function renderFixedExpenses(expenses) {
  const tbody = document.getElementById('fixed-expenses-tbody');
  let totalFixed = 0;

  tbody.innerHTML = expenses.map(item => {
    totalFixed += item.actual;
    const diff = item.actual - item.budget;
    return `
      <tr class="hover:bg-slate-800/30 transition text-slate-300">
        <td class="py-2.5 pr-2 font-medium text-slate-200">${item.name}</td>
        <td class="py-2.5 text-slate-400">${formatNIS(item.budget)}</td>
        <td class="py-2.5 font-semibold text-slate-200">${formatNIS(item.actual)}</td>
        <td class="py-2.5 ${diff > 0 ? 'text-rose-400' : 'text-slate-400'}">
          ${diff > 0 ? '+' : ''}${formatNIS(diff)}
        </td>
        <td class="py-2.5 pl-2">
          <span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-800 text-slate-400">קבוע</span>
        </td>
      </tr>
    `;
  }).join('');

  document.getElementById('fixed-exp-summary-total').innerText = `סה״כ הוצאות קבועות: ${formatNIS(totalFixed)}`;
}

// Initial Load
document.addEventListener('DOMContentLoaded', () => {
  fetchDashboardData();
});
