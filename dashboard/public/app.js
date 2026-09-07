/**
 * Ariel Fit & Spa / A+ Street Mall - Versatile Financial Dashboard
 * Supports: Cards View, Annual Trends & Charts View, Full 12-Month Matrix, and AI Insights.
 */

const _initNow = new Date();
let currentMonth = (_initNow.getMonth() + 1) || 9;
let currentClub = 'all';
let currentView = 'cards';
let currentSnapshot = null;
let currentMembershipsTableTab = 'cancels';
let dashboardData = null;
let activeModalItem = null;

let chartMain = null;
let chartTrainer = null;
let chartPT = null;
let chartUtilities = null;
let chartOverhead = null;
let chartCashflow = null;
let chartMemDist = null;
let chartMemTimeline = null;
let chartMemJoins = null;
let chartSeasonalMem = null;

let currentReasonPeriod = 'all';
let currentMemTypeClub = 'all';
let currentExpiringMonth = null;

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

// View Switcher (Cards | Memberships | Charts | Matrix)
function switchView(viewName) {
  currentView = viewName;

  document.querySelectorAll('.view-btn').forEach(btn => {
    btn.classList.remove('bg-rose-600', 'text-white', 'shadow-2xs');
    btn.classList.add('text-zinc-700', 'hover:bg-white');
  });

  const activeBtn = document.getElementById(`view-${viewName}`);
  if (activeBtn) {
    activeBtn.classList.remove('text-zinc-700', 'hover:bg-white');
    activeBtn.classList.add('bg-rose-600', 'text-white', 'shadow-2xs');
  }

  // Toggle View Containers
  document.getElementById('view-container-cards').classList.toggle('hidden', viewName !== 'cards');
  document.getElementById('view-container-memberships').classList.toggle('hidden', viewName !== 'memberships');
  document.getElementById('view-container-charts').classList.toggle('hidden', viewName !== 'charts');
  document.getElementById('view-container-matrix').classList.toggle('hidden', viewName !== 'matrix');
  const schedCont = document.getElementById('view-container-schedule');
  if (schedCont) {
    schedCont.classList.toggle('hidden', viewName !== 'schedule');
  }
  const supCont = document.getElementById('view-container-suppliers');
  if (supCont) {
    supCont.classList.toggle('hidden', viewName !== 'suppliers');
  }
  const tasksCont = document.getElementById('view-container-tasks');
  if (tasksCont) {
    tasksCont.classList.toggle('hidden', viewName !== 'tasks');
  }

  if (viewName === 'suppliers') {
    loadSuppliersDashboard();
  } else if (viewName === 'tasks') {
    loadTasksBoard();
  } else if (viewName === 'schedule') {
    loadScheduleAnalytics();
  } else if (viewName === 'charts' && dashboardData) {
    try {
      renderAnnualCharts(dashboardData.annual_trends);
    } catch (err) {
      console.warn('Charts render warning:', err);
    }
  } else if (viewName === 'memberships' && dashboardData) {
    try {
      renderMemberships(dashboardData);
      renderMembershipCharts(dashboardData.memberships);
    } catch (err) {
      console.warn('Memberships render warning:', err);
    }
  }
}

function setClub(club) {
  currentClub = club;

  // Club metadata configuration for distinct badges and labels
  const CLUB_CONFIG = {
    all: {
      label: 'כל המועדון (מאוחד)',
      dotColor: 'bg-emerald-400',
      badgeBg: 'bg-zinc-950 text-white border-zinc-800'
    },
    gym: {
      label: 'חדר כושר',
      dotColor: 'bg-blue-400',
      badgeBg: 'bg-blue-950 text-blue-100 border-blue-800'
    },
    pilates: {
      label: 'פילאטיס מכשירים',
      dotColor: 'bg-purple-400',
      badgeBg: 'bg-purple-950 text-purple-100 border-purple-800'
    }
  };

  // Reset all buttons to inactive state
  document.querySelectorAll('.club-tab-btn').forEach(btn => {
    btn.className = 'club-tab-btn px-4 py-1.5 rounded-lg transition-all text-xs font-semibold text-zinc-600 hover:text-zinc-900 hover:bg-zinc-200/70 flex items-center gap-1.5';
    const dot = btn.querySelector('span:first-child');
    if (dot) dot.className = 'w-1.5 h-1.5 rounded-full bg-transparent';
  });

  // Activate chosen button
  const activeBtn = document.getElementById(`club-${club}`);
  if (activeBtn) {
    activeBtn.className = 'club-tab-btn px-4 py-1.5 rounded-lg transition-all text-xs font-black bg-zinc-950 text-white shadow-md ring-1 ring-black/10 flex items-center gap-1.5';
    const dot = activeBtn.querySelector('span:first-child');
    if (dot) {
      const cfg = CLUB_CONFIG[club] || CLUB_CONFIG.all;
      dot.className = `w-1.5 h-1.5 rounded-full ${cfg.dotColor}`;
    }
  }

  // Update strip badge
  const cfg = CLUB_CONFIG[club] || CLUB_CONFIG.all;
  const stripBadge = document.getElementById('active-club-strip-badge');
  const stripText = document.getElementById('active-club-strip-text');
  if (stripText) stripText.innerText = cfg.label;
  if (stripBadge) {
    const dot = stripBadge.querySelector('span:first-child');
    if (dot) dot.className = `w-1.5 h-1.5 rounded-full ${cfg.dotColor}`;
  }

  fetchDashboardData();
}

function navigateMonth(direction) {
  currentMonth += direction;
  if (currentMonth < 1) currentMonth = 1;
  if (currentMonth > 12) currentMonth = 12;
  
  document.getElementById('current-month-display').innerText = `${MONTH_NAMES[currentMonth - 1]} 2026`;
  fetchDashboardData();
  if (currentView === 'schedule') {
    loadScheduleAnalytics();
  }
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
    const snapParam = currentSnapshot ? `&snapshot=${encodeURIComponent(currentSnapshot)}` : '';
    const res = await fetch(`/api/data?month=${currentMonth}&club=${currentClub}${snapParam}`);
    dashboardData = await res.json();
    renderDashboard(dashboardData);
  } catch (err) {
    console.error('Error loading dashboard data:', err);
  }
}

function openRevenueTargetModal() {
  if (!dashboardData || !dashboardData.summary) return;
  const rev = dashboardData.summary.total_revenue;
  const meta = dashboardData.metadata;

  const clubName = (currentClub === 'gym') ? 'חדר כושר' : ((currentClub === 'pilates') ? 'פילאטיס' : 'כל המועדון');
  document.getElementById('revenue-modal-subtitle').innerText = `${meta.month_name} ${meta.year} • ${clubName}`;
  document.getElementById('generic-revenue-budget-display').innerText = formatNIS(rev.generic_budget || rev.budget);
  document.getElementById('custom-revenue-input').value = Math.round(rev.budget);

  const modal = document.getElementById('revenue-target-modal');
  const card = document.getElementById('revenue-modal-card');
  modal.classList.remove('hidden');
  setTimeout(() => {
    modal.classList.remove('opacity-0');
    card.classList.remove('scale-95');
    card.classList.add('scale-100');
  }, 10);
  try { lucide.createIcons(); } catch (e) {}
}

function closeRevenueTargetModal() {
  const modal = document.getElementById('revenue-target-modal');
  const card = document.getElementById('revenue-modal-card');
  modal.classList.add('opacity-0');
  card.classList.remove('scale-100');
  card.classList.add('scale-95');
  setTimeout(() => {
    modal.classList.add('hidden');
  }, 200);
}

async function saveCustomRevenueTarget() {
  const inputVal = parseFloat(document.getElementById('custom-revenue-input').value);
  if (isNaN(inputVal) || inputVal < 0) {
    showToast('נא להזין סכום יעד תקין');
    return;
  }

  try {
    const res = await fetch('/api/target', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        club: currentClub,
        code: 'total_revenue',
        month: currentMonth,
        target: inputVal
      })
    });
    const data = await res.json();
    if (data.success) {
      showToast('יעד המכירות עודכן בהצלחה!');
      closeRevenueTargetModal();
      await fetchDashboardData();
    }
  } catch (err) {
    showToast('שגיאה בשמירת יעד מכירות');
  }
}

async function applyGenericRevenueTarget() {
  if (!dashboardData || !dashboardData.summary) return;
  const genericVal = dashboardData.summary.total_revenue.generic_budget;
  if (!genericVal) return;

  try {
    const res = await fetch('/api/target', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        club: currentClub,
        code: 'total_revenue',
        month: currentMonth,
        target: genericVal
      })
    });
    const data = await res.json();
    if (data.success) {
      showToast('הוחל יעד גנרי מתקציב 2026!');
      closeRevenueTargetModal();
      await fetchDashboardData();
    }
  } catch (err) {
    showToast('שגיאה בהחלת יעד גנרי');
  }
}

let currentProjectionType = 'revenue'; // 'revenue' | 'expenses'

function openProjectionModal(type) {
  if (!dashboardData || !dashboardData.summary) return;
  currentProjectionType = type;
  const isRev = type === 'revenue';
  const targetObj = isRev ? dashboardData.summary.total_revenue : dashboardData.summary.total_expenses;
  const meta = dashboardData.metadata;

  const clubName = (currentClub === 'gym') ? 'חדר כושר' : ((currentClub === 'pilates') ? 'פילאטיס' : 'כל המועדון');
  
  const titleEl = document.getElementById('projection-modal-title');
  const subEl = document.getElementById('projection-modal-subtitle');
  const iconEl = document.getElementById('projection-modal-icon');
  const iconBox = document.getElementById('projection-modal-icon-box');
  const calcDisplay = document.getElementById('calculated-projection-display');
  const inputEl = document.getElementById('custom-projection-input');

  if (titleEl) titleEl.innerText = isRev ? 'הגדרת תחזית הכנסות לסוף חודש' : 'הגדרת תחזית הוצאות לסוף חודש';
  if (subEl) subEl.innerText = `${clubName} • ${meta.month_name} ${meta.year}`;
  if (iconEl) iconEl.setAttribute('data-lucide', isRev ? 'trending-up' : 'trending-down');
  if (iconBox) {
    iconBox.className = `w-9 h-9 rounded-2xl ${isRev ? 'bg-rose-50 text-rose-600 border border-rose-100' : 'bg-zinc-100 text-zinc-700 border border-zinc-200'} flex items-center justify-center font-black`;
  }

  const calcVal = targetObj.calculated_projected || targetObj.actual || targetObj.budget;
  if (calcDisplay) calcDisplay.innerText = formatNIS(calcVal);
  if (inputEl) inputEl.value = Math.round(targetObj.projected);

  // Render 3-layer methodology breakdown
  const breakdownItemsEl = document.getElementById('projection-breakdown-items');
  const calcLabelEl = document.getElementById('projection-calc-label');
  if (calcLabelEl) {
    calcLabelEl.innerText = isRev ? 'תחזית הכנסות מחושבת (שקלול ערוצים)' : 'תחזית הוצאות מחושבת (מודל 3 שכבות)';
  }

  if (breakdownItemsEl) {
    const b = targetObj.breakdown;
    if (isRev && b) {
      breakdownItemsEl.innerHTML = `
        <div class="flex items-center justify-between py-1 border-b border-slate-100">
          <span class="flex items-center gap-1.5"><span class="w-2 h-2 rounded-full bg-emerald-500"></span> <strong>מנויים מתחדשים (MRR ארבוקס):</strong></span>
          <span class="font-bold text-slate-800">${formatNIS(b.stream1_mrr || 0)}</span>
        </div>
        <div class="flex items-center justify-between py-1 border-b border-slate-100">
          <span class="flex items-center gap-1.5"><span class="w-2 h-2 rounded-full bg-indigo-500"></span> <strong>אימונים אישיים וכרטיסיות:</strong></span>
          <span class="font-bold text-slate-800">${formatNIS(b.stream2_pt || 0)}</span>
        </div>
        <div class="flex items-center justify-between py-1">
          <span class="flex items-center gap-1.5"><span class="w-2 h-2 rounded-full bg-amber-500"></span> <strong>דמי הרשמה, סטודיו והכנסות נוספות:</strong></span>
          <span class="font-bold text-slate-800">${formatNIS(b.stream3_other || 0)}</span>
        </div>
      `;
    } else if (!isRev && b) {
      breakdownItemsEl.innerHTML = `
        <div class="flex items-center justify-between py-1 border-b border-slate-100">
          <span class="flex items-center gap-1.5"><span class="w-2 h-2 rounded-full bg-indigo-500"></span> <strong>שכבה 1: חוזים קבועים (שכירות, ניהול, ארנונה):</strong></span>
          <span class="font-bold text-slate-800">${formatNIS(b.layer1_fixed || 0)}</span>
        </div>
        <div class="flex items-center justify-between py-1 border-b border-slate-100">
          <span class="flex items-center gap-1.5"><span class="w-2 h-2 rounded-full bg-blue-500"></span> <strong>שכבה 2: שכר ומאמנים (ארבוקס + חילנט):</strong></span>
          <span class="font-bold text-slate-800">${formatNIS(b.layer2_staff || 0)}</span>
        </div>
        <div class="flex items-center justify-between py-1">
          <span class="flex items-center gap-1.5"><span class="w-2 h-2 rounded-full bg-amber-500"></span> <strong>שכבה 3: תפעול, חשמל עונתי ועמלות:</strong></span>
          <span class="font-bold text-slate-800">${formatNIS(b.layer3_ops || 0)}</span>
        </div>
      `;
    } else {
      breakdownItemsEl.innerHTML = `<div class="text-slate-400 py-1">משקלל נתוני ביצוע מאומתים ושיעורי ארבוקס</div>`;
    }
  }

  const modal = document.getElementById('projection-modal');
  const card = document.getElementById('projection-modal-card');
  modal.classList.remove('hidden');
  setTimeout(() => {
    modal.classList.remove('opacity-0');
    card.classList.remove('scale-95');
    card.classList.add('scale-100');
  }, 10);
  try { lucide.createIcons(); } catch (e) {}
}

function closeProjectionModal() {
  const modal = document.getElementById('projection-modal');
  const card = document.getElementById('projection-modal-card');
  if (!modal || !card) return;
  modal.classList.add('opacity-0');
  card.classList.remove('scale-100');
  card.classList.add('scale-95');
  setTimeout(() => {
    modal.classList.add('hidden');
  }, 200);
}

async function saveCustomProjection() {
  const inputVal = parseFloat(document.getElementById('custom-projection-input').value);
  if (isNaN(inputVal) || inputVal < 0) {
    showToast('נא להזין סכום תחזית תקין');
    return;
  }

  const codeKey = currentProjectionType === 'revenue' ? 'projected_revenue' : 'projected_expenses';

  try {
    const res = await fetch('/api/target', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        club: currentClub,
        code: codeKey,
        month: currentMonth,
        target: inputVal
      })
    });
    const data = await res.json();
    if (data.success) {
      showToast('התחזית נשמרה בהצלחה!');
      closeProjectionModal();
      await fetchDashboardData();
    }
  } catch (err) {
    showToast('שגיאה בשמירת התחזית');
  }
}

async function applyCalculatedProjection() {
  const codeKey = currentProjectionType === 'revenue' ? 'projected_revenue' : 'projected_expenses';

  try {
    const res = await fetch('/api/target', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        club: currentClub,
        code: codeKey,
        month: currentMonth,
        target: null
      })
    });
    const data = await res.json();
    if (data.success) {
      showToast('הוחלה תחזית מחושבת!');
      closeProjectionModal();
      await fetchDashboardData();
    }
  } catch (err) {
    showToast('שגיאה באיפוס התחזית');
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

  const customBadge = document.getElementById('strip-rev-custom-badge');
  if (customBadge) {
    customBadge.classList.toggle('hidden', !sum.total_revenue.is_custom);
  }

  const customRevProjBadge = document.getElementById('strip-rev-proj-custom-badge');
  if (customRevProjBadge) {
    customRevProjBadge.classList.toggle('hidden', !sum.total_revenue.is_custom_projected);
  }

  document.getElementById('strip-exp-actual').innerText = formatNIS(sum.total_expenses.actual);
  document.getElementById('strip-exp-budget').innerText = formatNIS(sum.total_expenses.budget);
  document.getElementById('strip-exp-pct').innerText = `${sum.total_expenses.pct}%`;
  document.getElementById('strip-exp-proj').innerText = formatNIS(sum.total_expenses.projected);

  const customExpProjBadge = document.getElementById('strip-exp-proj-custom-badge');
  if (customExpProjBadge) {
    customExpProjBadge.classList.toggle('hidden', !sum.total_expenses.is_custom_projected);
  }

  // 0. Render Live Revenue Pacing Tracker (קצב יומי נדרש ופער מול היעד)
  renderPacingTracker(data.pacing_tracker);

  // 1. Render AI Smart Insights
  renderSmartInsights(data.smart_insights);

  // 2. Render Cards View (View 1)
  renderRevenueBreakdown(data.revenue_breakdown);
  renderCategoryCards(data.incomes, 'incomes-cards-container', 'income');
  renderCategoryCards(data.variable_expenses, 'expenses-cards-container', 'expense');
  renderFixedCards(data.fixed_expenses);

  // 3. Render Memberships View
  renderMemberships(data);

  // 4. Render Charts View (View 2)
  if (currentView === 'charts') {
    renderAnnualCharts(data.annual_trends);
  }

  // 5. Render Matrix View (View 3)
  renderFinancialMatrix(data.incomes, data.variable_expenses, data.fixed_expenses);

  try {
    lucide.createIcons();
  } catch (e) {}
}

function renderPacingTracker(pacing) {
  const container = document.getElementById('pacing-tracker-container');
  if (!container || !pacing) return;

  // 1. Status Badge
  const badge = document.getElementById('pacing-status-badge');
  if (badge) {
    badge.innerText = pacing.status_label || 'פעיל';
    badge.className = 'px-2.5 py-0.5 rounded-full text-[11px] font-black border transition-colors';
    if (pacing.status === 'ahead') {
      badge.classList.add('bg-emerald-50', 'text-emerald-700', 'border-emerald-200');
    } else if (pacing.status === 'on_track') {
      badge.classList.add('bg-indigo-50', 'text-indigo-700', 'border-indigo-200');
    } else if (pacing.status === 'behind') {
      badge.classList.add('bg-rose-50', 'text-rose-700', 'border-rose-200');
    } else if (pacing.status === 'completed') {
      badge.classList.add('bg-slate-100', 'text-slate-700', 'border-slate-300');
    } else {
      badge.classList.add('bg-blue-50', 'text-blue-700', 'border-blue-200');
    }
  }

  // 2. Subtitle
  const subtitle = document.getElementById('pacing-subtitle-display');
  if (subtitle) {
    if (pacing.is_current_month) {
      subtitle.innerText = `מעקב יומי שוטף לקבלת החלטות ותדרוך צוות מכירות • יום ${pacing.current_day} מתוך ${pacing.days_in_month}`;
    } else {
      subtitle.innerText = `סיכום ביצוע מול יעד מוגדר לחודש (${formatNIS(pacing.target)})`;
    }
  }

  // 3. Benchmark to Date
  const benchDisplay = document.getElementById('pacing-benchmark-display');
  if (benchDisplay) {
    benchDisplay.innerText = formatNIS(pacing.benchmark_to_date);
  }
  const benchSub = document.getElementById('pacing-benchmark-sub');
  if (benchSub) {
    benchSub.innerText = pacing.is_current_month 
      ? `נורמה ל-${pacing.current_day} ימים שחלפו (${pacing.time_elapsed_pct}% מהחודש)`
      : `יעד כולל לחודש מלא`;
  }

  // 4. Pacing Gap
  const gapDisplay = document.getElementById('pacing-gap-display');
  const gapSub = document.getElementById('pacing-gap-sub');
  if (gapDisplay) {
    const gap = pacing.revenue_gap_to_pace;
    if (gap >= 0) {
      gapDisplay.innerText = `+${formatNIS(gap)}`;
      gapDisplay.className = 'text-lg font-black text-emerald-600';
      if (gapSub) {
        gapSub.innerText = 'עודף מעל קצב התקדמות הזמן 🚀';
        gapSub.className = 'text-[10px] font-bold text-emerald-600';
      }
    } else {
      gapDisplay.innerText = `-${formatNIS(Math.abs(gap))}`;
      gapDisplay.className = 'text-lg font-black text-rose-600';
      if (gapSub) {
        gapSub.innerText = 'פער מול הנורמה להיום ⚠️';
        gapSub.className = 'text-[10px] font-bold text-rose-600';
      }
    }
  }

  // 5. Required Daily Rate (CRITICAL FOR IDAN)
  const reqRateDisplay = document.getElementById('pacing-required-rate-display');
  const remDaysSub = document.getElementById('pacing-remaining-days-sub');
  if (reqRateDisplay) {
    if (pacing.status === 'completed') {
      reqRateDisplay.innerText = 'החודש הושלם';
      reqRateDisplay.className = 'text-lg font-black text-slate-600';
    } else {
      reqRateDisplay.innerText = `${formatNIS(pacing.daily_rate_required)} / יום`;
      reqRateDisplay.className = 'text-lg font-black text-indigo-700';
    }
  }
  if (remDaysSub) {
    if (pacing.status === 'completed') {
      remDaysSub.innerText = 'ביצוע סופי רשום';
    } else {
      remDaysSub.innerText = `יעד יומי לצוות מכירות (${pacing.days_remaining} ימים שנותרו)`;
    }
  }

  // 6. Projected Month-End
  const projEndDisplay = document.getElementById('pacing-projected-end-display');
  const projPctSub = document.getElementById('pacing-projected-pct-sub');
  if (projEndDisplay) {
    projEndDisplay.innerText = formatNIS(pacing.projected_month_end);
  }
  if (projPctSub) {
    const projPct = pacing.target > 0 ? Math.round((pacing.projected_month_end / pacing.target) * 100) : 100;
    projPctSub.innerText = `צפי עמידה ביעד: ${projPct}% (${formatNIS(pacing.projected_month_end)} מתוך ${formatNIS(pacing.target)})`;
  }

  // 7. Dual Bar
  const ratioLabel = document.getElementById('pacing-progress-ratio-label');
  if (ratioLabel) {
    ratioLabel.innerText = `יום ${pacing.current_day} מתוך ${pacing.days_in_month} • נותרו ${pacing.days_remaining} ימים לסגירת החודש`;
  }

  const timePctText = document.getElementById('pacing-time-pct-text');
  const timeBar = document.getElementById('pacing-time-bar');
  if (timePctText) timePctText.innerText = `${pacing.time_elapsed_pct}%`;
  if (timeBar) timeBar.style.width = `${Math.min(100, Math.max(0, pacing.time_elapsed_pct))}%`;

  const moneyPctText = document.getElementById('pacing-money-pct-text');
  const moneyBar = document.getElementById('pacing-money-bar');
  if (moneyPctText) {
    moneyPctText.innerText = `${pacing.money_progress_pct}% (${formatNIS(pacing.actual)} מתוך ${formatNIS(pacing.target)})`;
  }
  if (moneyBar) {
    moneyBar.style.width = `${Math.min(100, Math.max(0, pacing.money_progress_pct))}%`;
    moneyBar.className = 'h-full rounded-full transition-all duration-500 shadow-2xs ' + 
      (pacing.status === 'ahead' ? 'bg-emerald-500' : (pacing.status === 'behind' ? 'bg-rose-500' : 'bg-indigo-600'));
  }

  // 8. Management Action Insight
  const insightText = document.getElementById('pacing-insight-text');
  const insightContainer = document.getElementById('pacing-insight-container');
  if (insightText) {
    insightText.innerText = pacing.insight || '';
  }
  if (insightContainer) {
    insightContainer.className = 'p-2.5 rounded-xl text-xs font-medium flex items-center gap-2.5 ' +
      (pacing.status === 'ahead' 
        ? 'bg-emerald-50 text-emerald-900 border border-emerald-200' 
        : (pacing.status === 'behind'
          ? 'bg-rose-50 text-rose-900 border border-rose-200'
          : 'bg-indigo-50 text-indigo-900 border border-indigo-200'));
  }

  try {
    lucide.createIcons();
  } catch (e) {}
}

function renderSmartInsights(tips) {
  const container = document.getElementById('smart-insights-section');
  if (!tips || tips.length === 0) {
    container.innerHTML = '';
    return;
  }

  container.innerHTML = `
    <div class="p-4 bg-gradient-to-r from-zinc-950 via-zinc-900 to-black rounded-2xl border border-zinc-800 shadow-sm space-y-3 text-white">
      <div class="flex items-center justify-between border-b border-zinc-800/80 pb-2.5">
        <span class="text-xs font-black text-white flex items-center gap-2">
          <span class="w-2.5 h-2.5 rounded-full bg-rose-500 animate-pulse shadow-sm"></span>
          <i data-lucide="sparkles" class="w-4 h-4 text-rose-500"></i>
          <span>תובנות חכמות, התראות ודגלים דחופים (AI Pulse)</span>
        </span>
        <div class="flex items-center gap-2">
          <span class="text-[10px] text-zinc-400 font-medium">סנכרון תפעולי בלייב</span>
          <span class="text-[10px] bg-rose-600 text-white font-black px-2.5 py-0.5 rounded-full shadow-2xs">LIVE</span>
        </div>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-3 pt-0.5">
        ${tips.map(t => {
          const isUrgent = t.priority === 'urgent';
          const isWarning = t.priority === 'warning';
          const isSuccess = t.priority === 'success';

          let borderClass = 'border-zinc-800 bg-zinc-900/90';
          let tagBadge = 'bg-zinc-800 text-zinc-300 border-zinc-700';
          let iconColor = 'text-indigo-400';

          if (isUrgent) {
            borderClass = 'border-rose-600/70 bg-gradient-to-br from-rose-950/30 to-zinc-900/95';
            tagBadge = 'bg-rose-500/20 text-rose-300 border-rose-500/40 animate-pulse';
            iconColor = 'text-rose-500';
          } else if (isWarning) {
            borderClass = 'border-amber-600/60 bg-gradient-to-br from-amber-950/20 to-zinc-900/95';
            tagBadge = 'bg-amber-500/20 text-amber-300 border-amber-500/40';
            iconColor = 'text-amber-400';
          } else if (isSuccess) {
            borderClass = 'border-emerald-600/60 bg-gradient-to-br from-emerald-950/20 to-zinc-900/95';
            tagBadge = 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40';
            iconColor = 'text-emerald-400';
          }

          return `
            <div class="p-3.5 rounded-xl border ${borderClass} flex items-start gap-3 text-xs shadow-2xs transition-all hover:border-zinc-600">
              <div class="w-7 h-7 rounded-lg bg-zinc-800/80 flex items-center justify-center flex-shrink-0 mt-0.5 border border-zinc-700/50">
                <i data-lucide="${t.icon || 'zap'}" class="w-4 h-4 ${iconColor}"></i>
              </div>
              <div class="flex-1 min-w-0">
                <div class="flex items-center justify-between gap-2 mb-1 flex-wrap">
                  <strong class="font-black text-zinc-100 text-xs">${t.title}</strong>
                  ${t.tag ? `<span class="px-2 py-0.5 text-[9.5px] font-black rounded-md border ${tagBadge}">${t.tag}</span>` : ''}
                </div>
                <p class="text-zinc-300 text-[11px] leading-relaxed">${t.text}</p>
              </div>
            </div>
          `;
        }).join('')}
      </div>
    </div>
  `;

  try { lucide.createIcons(); } catch (e) {}
}

function renderCategoryCards(items, containerId, type) {
  const container = document.getElementById(containerId);
  container.innerHTML = '';

  if (!items || items.length === 0) {
    container.innerHTML = '<div class="text-xs text-zinc-400 p-4 text-center">אין נתונים לחודש זה</div>';
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
        statusHTML = `<span class="text-xs font-medium text-zinc-500">נשאר לגבות ₪${Math.max(Math.round(b - a), 0).toLocaleString('he-IL')}</span>`;
      }
    } else {
      if (a > b && b > 0) {
        statusHTML = `<span class="text-xs font-black text-rose-700 bg-rose-50 px-2 py-0.5 rounded-md border border-rose-200 flex items-center gap-1">
          <span class="w-3.5 h-3.5 rounded-full bg-rose-600 text-white flex items-center justify-center text-[9px] font-black">!</span>
          חריגה של ₪${Math.round(a - b).toLocaleString('he-IL')}
        </span>`;
      } else {
        statusHTML = `<span class="text-xs font-medium text-zinc-500">נשאר להוציא ₪${Math.max(Math.round(b - a), 0).toLocaleString('he-IL')}</span>`;
      }
    }

    const card = document.createElement('div');
    card.className = 'app-card p-4 sm:p-5 flex flex-col justify-between cursor-pointer border border-zinc-200/80 hover:border-zinc-300';
    card.onclick = (e) => {
      if (e.target.closest('.tx-drawer-btn') || e.target.closest('.tx-drawer-box')) return;
      openDrilldownModal(item);
    };

    const itemId = `card-tx-${type}-${idx}`;
    const barColorClass = isIncome ? 'bg-emerald-500' : 'bg-rose-600';
    const textAmountColor = isIncome ? 'text-zinc-900' : 'text-zinc-900';

    card.innerHTML = `
      <div>
        <div class="flex items-center justify-between mb-3">
          <div class="flex items-center gap-2 flex-wrap">
            <h3 class="text-base font-black text-zinc-900">${item.name}</h3>
            ${item.club ? `<span class="text-[10px] font-bold px-2 py-0.5 bg-zinc-100 text-zinc-700 rounded-md border border-zinc-200/60">${item.club}</span>` : ''}
            ${item.is_contract ? `<span class="text-[10px] font-bold px-2 py-0.5 bg-amber-50 text-amber-900 rounded-md border border-amber-200/80 flex items-center gap-1"><span>🏷️</span><span>${item.contract_tag}</span></span>` : ''}
          </div>
          <button class="text-zinc-400 hover:text-zinc-700 p-1">
            <i data-lucide="more-vertical" class="w-4 h-4"></i>
          </button>
        </div>

        <div class="flex items-baseline justify-between mb-2">
          <div>
            <span class="text-[11px] text-zinc-400 block font-medium">${isIncome ? 'צפוי להכנס' : 'צפוי לצאת / יעד'}</span>
            <span class="text-sm font-bold text-zinc-600">${formatNIS(b)}</span>
          </div>
          <div class="text-left">
            <span class="text-[11px] text-zinc-400 block font-medium">${isIncome ? 'נכנס בפועל' : 'יצא בפועל'}</span>
            ${(isIncome && a === 0 && item.actual_estimated) ? `
              <div class="flex items-baseline gap-1.5 justify-end">
                <span class="text-lg font-black text-slate-400" title="צפי נוכחי מחושב מתוך דוח קבלות/ארבוקס (${item.actual_estimated_source || ''})">${formatNIS(item.actual_estimated)}</span>
                <span class="text-[10px] font-bold text-slate-500 bg-slate-100 border border-slate-200 px-1.5 py-0.5 rounded-md">צפי (קבלות)</span>
              </div>
            ` : `
              <span class="text-lg font-black ${textAmountColor}">${formatNIS(a)}</span>
            `}
          </div>
        </div>

        <div class="w-full bg-zinc-100 h-2 rounded-full overflow-hidden mb-2.5">
          <div class="${barColorClass} h-full rounded-full transition-all duration-500" style="width: ${pct}%"></div>
        </div>

        <div class="flex items-center justify-between pt-1">
          <div>${statusHTML}</div>
          <button onclick="toggleCardTransactions('${itemId}')" class="tx-drawer-btn text-xs font-semibold text-zinc-500 hover:text-zinc-900 flex items-center gap-1 transition">
            <span>פירוט חודשי</span>
            <i data-lucide="chevron-down" id="icon-${itemId}" class="w-3.5 h-3.5 transition-transform"></i>
          </button>
        </div>
      </div>

      <div id="${itemId}" class="tx-drawer-box hidden mt-3 pt-3 border-t border-zinc-100 space-y-1.5">
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

  const mainEl = document.querySelector("#annual-main-chart");
  const trainerEl = document.querySelector("#trainer-trend-chart");
  const ptEl = document.querySelector("#pt-trend-chart");

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
    colors: ['#10b981', '#e11d48', '#18181b'],
    plotOptions: {
      bar: { horizontal: false, columnWidth: '55%', borderRadius: 6 }
    },
    dataLabels: { enabled: false },
    stroke: { show: true, width: 2, colors: ['transparent'] },
    xaxis: { categories: trends.months_labels, labels: { style: { fontWeight: 600 } } },
    yaxis: {
      labels: { formatter: (val) => '₪' + (val / 1000).toFixed(0) + 'k' }
    },
    tooltip: { y: { formatter: (val) => formatNIS(val) } }
  };

  if (chartMain) { try { chartMain.destroy(); } catch (e) {} }
  if (mainEl) {
    mainEl.innerHTML = '';
    chartMain = new ApexCharts(mainEl, mainOpts);
    chartMain.render();
  }

  // Chart 2: Trainer Labor Trend
  const trainerOpts = {
    series: [{ name: 'עלות שכר מאמנים והדרכה', data: trends.trainers }],
    chart: { type: 'area', height: 240, fontFamily: 'Heebo, sans-serif', toolbar: { show: false } },
    colors: ['#e11d48'],
    dataLabels: { enabled: false },
    stroke: { curve: 'smooth', width: 3 },
    fill: { type: 'gradient', gradient: { opacityFrom: 0.55, opacityTo: 0.05 } },
    xaxis: { categories: trends.months_labels, labels: { style: { fontWeight: 600 } } },
    yaxis: { labels: { formatter: (val) => '₪' + (val / 1000).toFixed(0) + 'k' } },
    tooltip: { y: { formatter: (val) => formatNIS(val) } }
  };

  if (chartTrainer) { try { chartTrainer.destroy(); } catch (e) {} }
  if (trainerEl) {
    trainerEl.innerHTML = '';
    chartTrainer = new ApexCharts(trainerEl, trainerOpts);
    chartTrainer.render();
  }

  // Chart 3: PT Profitability Trend
  const ptOpts = {
    series: [
      { name: 'הכנסות אישיים', data: trends.pt.revenue },
      { name: 'עלות מאמנים אישיים', data: trends.pt.cost }
    ],
    chart: { type: 'line', height: 240, fontFamily: 'Heebo, sans-serif', toolbar: { show: false } },
    colors: ['#10b981', '#e11d48'],
    stroke: { width: [3, 3], curve: 'straight' },
    xaxis: { categories: trends.months_labels, labels: { style: { fontWeight: 600 } } },
    yaxis: { labels: { formatter: (val) => '₪' + (val / 1000).toFixed(0) + 'k' } },
    tooltip: { y: { formatter: (val) => formatNIS(val) } }
  };

  if (chartPT) { try { chartPT.destroy(); } catch (e) {} }
  if (ptEl) {
    ptEl.innerHTML = '';
    chartPT = new ApexCharts(ptEl, ptOpts);
    chartPT.render();
  }

  // Chart 4: Utilities & Facility Maintenance (חשמל, מים, מיזוג, אחזקה ותקלות)
  const utilEl = document.querySelector("#utilities-trend-chart");
  if (utilEl && trends.utilities) {
    const u = trends.utilities;
    const utilOpts = {
      series: [
        { name: 'חשמל ומז״א', data: u.electricity },
        { name: 'מים', data: u.water },
        { name: 'הסכם שירות מיזוג', data: u.hvac },
        { name: 'אחזקה, ציוד ותקלות', data: u.maintenance }
      ],
      chart: {
        type: 'bar',
        height: 280,
        stacked: false,
        fontFamily: 'Heebo, sans-serif',
        toolbar: { show: false }
      },
      colors: ['#f59e0b', '#06b6d4', '#3b82f6', '#f43f5e'],
      plotOptions: {
        bar: {
          horizontal: false,
          columnWidth: '60%',
          borderRadius: 4
        }
      },
      dataLabels: { enabled: false },
      stroke: { show: true, width: 2, colors: ['transparent'] },
      xaxis: {
        categories: trends.months_labels,
        labels: { style: { fontWeight: 600 } }
      },
      yaxis: {
        labels: { formatter: (val) => '₪' + (val / 1000).toFixed(0) + 'k' }
      },
      legend: {
        position: 'top',
        horizontalAlign: 'right',
        fontSize: '12px',
        fontWeight: 600
      },
      tooltip: {
        y: { formatter: (val) => formatNIS(val) }
      }
    };

    if (chartUtilities) { try { chartUtilities.destroy(); } catch (e) {} }
    utilEl.innerHTML = '';
    chartUtilities = new ApexCharts(utilEl, utilOpts);
    chartUtilities.render();
  }

  // Chart 5: Operational Overhead (שיווק ופרסום, ניקיון, ארנונה)
  const overheadEl = document.querySelector("#overhead-trend-chart");
  if (overheadEl && trends.utilities) {
    const u = trends.utilities;
    const overheadOpts = {
      series: [
        { name: 'שיווק ופרסום', data: u.marketing },
        { name: 'ניקיון וחומרים', data: u.cleaning },
        { name: 'ארנונה', data: u.arnona }
      ],
      chart: {
        type: 'line',
        height: 250,
        fontFamily: 'Heebo, sans-serif',
        toolbar: { show: false }
      },
      colors: ['#4f46e5', '#059669', '#7c3aed'],
      stroke: {
        width: [3, 3, 2.5],
        curve: 'smooth',
        dashArray: [0, 0, 4]
      },
      dataLabels: { enabled: false },
      xaxis: {
        categories: trends.months_labels,
        labels: { style: { fontWeight: 600 } }
      },
      yaxis: {
        labels: { formatter: (val) => '₪' + (val / 1000).toFixed(0) + 'k' }
      },
      legend: {
        position: 'top',
        horizontalAlign: 'right',
        fontSize: '12px',
        fontWeight: 600
      },
      tooltip: {
        y: { formatter: (val) => formatNIS(val) }
      }
    };

    if (chartOverhead) { try { chartOverhead.destroy(); } catch (e) {} }
    overheadEl.innerHTML = '';
    chartOverhead = new ApexCharts(overheadEl, overheadOpts);
    chartOverhead.render();
  }

  // Chart 6: Cash Flow Trajectory & Net Flow (תזרים נכנס מול יוצא ויתרות בנק)
  const cashflowEl = document.querySelector("#cashflow-trend-chart");
  if (cashflowEl && trends.cash_flow) {
    const cf = trends.cash_flow;
    const cashflowOpts = {
      series: [
        { name: 'תזרים נכנס (הכנסות)', type: 'column', data: cf.inflow },
        { name: 'תזרים יוצא (הוצאות וספקים)', type: 'column', data: cf.outflow },
        { name: 'תזרים נקי (Net)', type: 'line', data: cf.net }
      ],
      chart: {
        height: 280,
        type: 'line',
        stacked: false,
        fontFamily: 'Heebo, sans-serif',
        toolbar: { show: false }
      },
      stroke: {
        width: [0, 0, 3],
        curve: 'smooth'
      },
      plotOptions: {
        bar: {
          columnWidth: '55%',
          borderRadius: 4
        }
      },
      colors: ['#10b981', '#f43f5e', '#6366f1'],
      xaxis: {
        categories: trends.months_labels,
        labels: { style: { fontWeight: 600 } }
      },
      yaxis: {
        labels: { formatter: (val) => '₪' + (val / 1000).toFixed(0) + 'k' }
      },
      legend: {
        position: 'top',
        horizontalAlign: 'right',
        fontSize: '12px',
        fontWeight: 600
      },
      tooltip: {
        y: { formatter: (val) => formatNIS(val) }
      }
    };

    if (chartCashflow) { try { chartCashflow.destroy(); } catch (e) {} }
    cashflowEl.innerHTML = '';
    chartCashflow = new ApexCharts(cashflowEl, cashflowOpts);
    chartCashflow.render();
  }
}

// =========================================================================
// FULL FINANCIAL MATRIX (VIEW 3)
// =========================================================================
function renderFinancialMatrix(incomes, varExp, fixExp) {
  const thead = document.getElementById('matrix-thead');
  const tbody = document.getElementById('matrix-tbody');
  const tfoot = document.getElementById('matrix-tfoot');
  if (!tbody) return;

  const monthsRange = [1, 2, 3, 4, 5, 6, 7];

  if (thead) {
    thead.innerHTML = `
      <tr>
        <th class="py-2.5 px-3">סעיף תקציבי</th>
        <th class="py-2.5 px-2">סוג</th>
        <th class="py-2.5 px-2">תקציב חודשי</th>
        ${monthsRange.map(mNum => {
          const mName = MONTH_NAMES[mNum - 1];
          const isSelected = (mNum === currentMonth);
          return `<th class="py-2.5 px-2 text-center ${isSelected ? 'bg-blue-600 text-white font-black rounded-t-xl' : ''}">${mName}${isSelected ? ' (פעיל)' : ''}</th>`;
        }).join('')}
        <th class="py-2.5 px-3 text-center bg-slate-900 text-white font-black rounded-t-xl">סה״כ מצטבר (YTD)</th>
      </tr>
    `;
  }

  tbody.innerHTML = '';

  const allItems = [
    ...incomes.map(x => ({ ...x, group: 'הכנסה', groupClass: 'text-emerald-700 bg-emerald-50' })),
    ...varExp.map(x => ({ ...x, group: 'משתנה', groupClass: 'text-blue-700 bg-blue-50' })),
    ...fixExp.map(x => ({ ...x, group: 'קבוע', groupClass: 'text-slate-700 bg-slate-100' }))
  ];

  tbody.innerHTML = allItems.map(item => {
    const months = item.all_months || {};
    const rowYTD = monthsRange.reduce((acc, mNum) => acc + (months[mNum]?.actual || 0), 0);

    return `
      <tr class="hover:bg-slate-50 transition cursor-pointer" onclick='openDrilldownModal(${JSON.stringify(item)})'>
        <td class="py-2.5 px-3 font-bold text-slate-900 flex items-center gap-1.5">
          <span>${item.name}</span>
          ${item.is_contract ? `<span class="text-[9px] px-1.5 py-0.2 rounded font-bold bg-amber-100/90 text-amber-900 border border-amber-300">הסכם</span>` : ''}
        </td>
        <td class="py-2.5 px-2"><span class="px-2 py-0.5 rounded text-[10px] font-bold ${item.groupClass}">${item.group}</span></td>
        <td class="py-2.5 px-2 font-medium text-slate-500">${formatNIS(item.budget)}</td>
        ${monthsRange.map(mNum => {
          const isSelected = (mNum === currentMonth);
          const val = months[mNum]?.actual || 0;
          return `<td class="py-2.5 px-2 text-center ${isSelected ? 'bg-blue-50/80 font-black text-blue-700' : (mNum > currentMonth ? 'text-slate-400' : '')}">${formatNIS(val)}</td>`;
        }).join('')}
        <td class="py-2.5 px-3 text-center font-bold text-slate-900 bg-slate-50/80">${formatNIS(rowYTD)}</td>
      </tr>
    `;
  }).join('');

  if (tfoot) {
    // 1. Incomes Sums
    const incBudget = incomes.reduce((acc, x) => acc + (x.budget || 0), 0);
    const incMonthly = monthsRange.map(mNum => incomes.reduce((acc, x) => acc + (x.all_months?.[mNum]?.actual || 0), 0));
    const incYTD = incMonthly.reduce((acc, v) => acc + v, 0);

    // 2. Variable Expenses Sums
    const varBudget = varExp.reduce((acc, x) => acc + (x.budget || 0), 0);
    const varMonthly = monthsRange.map(mNum => varExp.reduce((acc, x) => acc + (x.all_months?.[mNum]?.actual || 0), 0));
    const varYTD = varMonthly.reduce((acc, v) => acc + v, 0);

    // 3. Fixed Expenses Sums
    const fixBudget = fixExp.reduce((acc, x) => acc + (x.budget || 0), 0);
    const fixMonthly = monthsRange.map(mNum => fixExp.reduce((acc, x) => acc + (x.all_months?.[mNum]?.actual || 0), 0));
    const fixYTD = fixMonthly.reduce((acc, v) => acc + v, 0);

    // 4. Total Expenses Sums
    const totalExpBudget = varBudget + fixBudget;
    const totalExpMonthly = monthsRange.map((mNum, idx) => varMonthly[idx] + fixMonthly[idx]);
    const totalExpYTD = varYTD + fixYTD;

    // 5. Operating Profit Sums
    const profitBudget = incBudget - totalExpBudget;
    const profitMonthly = monthsRange.map((mNum, idx) => incMonthly[idx] - totalExpMonthly[idx]);
    const profitYTD = incYTD - totalExpYTD;

    tfoot.innerHTML = `
      <!-- Total Incomes -->
      <tr class="bg-emerald-50 text-emerald-950 font-black border-t-2 border-emerald-300">
        <td class="py-3 px-3 text-sm">🟢 סה״כ הכנסות</td>
        <td class="py-3 px-2 text-[11px]"><span class="px-2 py-0.5 rounded bg-emerald-200 text-emerald-900 font-bold">הכנסה</span></td>
        <td class="py-3 px-2 text-left">${formatNIS(incBudget)}</td>
        ${incMonthly.map((val, idx) => {
          const isSelected = ((idx + 1) === currentMonth);
          return `<td class="py-3 px-2 text-center ${isSelected ? 'bg-emerald-200/80 font-black text-emerald-950 text-sm' : ''}">${formatNIS(val)}</td>`;
        }).join('')}
        <td class="py-3 px-3 text-center bg-emerald-100/80 text-sm">${formatNIS(incYTD)}</td>
      </tr>

      <!-- Total Variable Expenses -->
      <tr class="bg-blue-50/70 text-blue-950 font-bold border-t border-slate-200">
        <td class="py-2.5 px-3">🔵 סה״כ הוצאות משתנות</td>
        <td class="py-2.5 px-2 text-[11px]"><span class="px-2 py-0.5 rounded bg-blue-200 text-blue-900 font-bold">משתנה</span></td>
        <td class="py-2.5 px-2 text-left">${formatNIS(varBudget)}</td>
        ${varMonthly.map((val, idx) => {
          const isSelected = ((idx + 1) === currentMonth);
          return `<td class="py-2.5 px-2 text-center ${isSelected ? 'bg-blue-200/80 font-black text-blue-950' : ''}">${formatNIS(val)}</td>`;
        }).join('')}
        <td class="py-2.5 px-3 text-center bg-blue-100/80 font-bold">${formatNIS(varYTD)}</td>
      </tr>

      <!-- Total Fixed Expenses -->
      <tr class="bg-slate-100/80 text-slate-900 font-bold border-t border-slate-200">
        <td class="py-2.5 px-3">⚪ סה״כ הוצאות קבועות</td>
        <td class="py-2.5 px-2 text-[11px]"><span class="px-2 py-0.5 rounded bg-slate-300 text-slate-800 font-bold">קבוע</span></td>
        <td class="py-2.5 px-2 text-left">${formatNIS(fixBudget)}</td>
        ${fixMonthly.map((val, idx) => {
          const isSelected = ((idx + 1) === currentMonth);
          return `<td class="py-2.5 px-2 text-center ${isSelected ? 'bg-slate-300/80 font-black text-slate-950' : ''}">${formatNIS(val)}</td>`;
        }).join('')}
        <td class="py-2.5 px-3 text-center bg-slate-200 font-bold">${formatNIS(fixYTD)}</td>
      </tr>

      <!-- Total All Expenses -->
      <tr class="bg-rose-50 text-rose-950 font-black border-t-2 border-rose-200">
        <td class="py-3 px-3 text-sm">🔴 סה״כ כלל ההוצאות</td>
        <td class="py-3 px-2 text-[11px]"><span class="px-2 py-0.5 rounded bg-rose-200 text-rose-900 font-bold">הוצאות</span></td>
        <td class="py-3 px-2 text-left">${formatNIS(totalExpBudget)}</td>
        ${totalExpMonthly.map((val, idx) => {
          const isSelected = ((idx + 1) === currentMonth);
          return `<td class="py-3 px-2 text-center ${isSelected ? 'bg-rose-200/80 font-black text-rose-950 text-sm' : ''}">${formatNIS(val)}</td>`;
        }).join('')}
        <td class="py-3 px-3 text-center bg-rose-100/80 text-sm">${formatNIS(totalExpYTD)}</td>
      </tr>

      <!-- Net Operating Profit -->
      <tr class="bg-slate-900 text-white font-black text-xs border-t-2 border-slate-950">
        <td class="py-3 px-3 text-sm flex items-center gap-1.5">
          <span>💼</span>
          <span>רווח תפעולי נקי (EBITDA)</span>
        </td>
        <td class="py-3 px-2 text-[10px]"><span class="px-2 py-0.5 rounded bg-slate-700 text-slate-200 font-bold">רווח</span></td>
        <td class="py-3 px-2 text-left text-slate-200">${formatNIS(profitBudget)}</td>
        ${profitMonthly.map((val, idx) => {
          const isSelected = ((idx + 1) === currentMonth);
          const isPositive = val >= 0;
          return `<td class="py-3 px-2 text-center ${isSelected ? 'bg-blue-600 font-black text-sm' : (isPositive ? 'text-emerald-400' : 'text-rose-400')}">${formatNIS(val)}</td>`;
        }).join('')}
        <td class="py-3 px-3 text-center text-sm ${profitYTD >= 0 ? 'text-emerald-300' : 'text-rose-300'}">${formatNIS(profitYTD)}</td>
      </tr>
    `;
  }
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
  const isClosedMonth = currentMonth < 8;
  const forecastText = isClosedMonth
    ? `ביצוע סופי (חודש סגור): ${formatNIS(item.actual || item.projected)}`
    : `תחזית חכמה לסוף חודש: ${formatNIS(item.projected)} (מבוסס קצב יומי)`;
  document.getElementById('modal-forecast-amount').innerText = forecastText;
  document.getElementById('modal-explanation-text').innerText = item.explanation || 'סעיף תקציבי שוטף מתוך פעילות המועדון.';

  // Contract Info Box in modal
  const contractBox = document.getElementById('modal-contract-box');
  if (contractBox) {
    if (item.is_contract) {
      contractBox.classList.remove('hidden');
      document.getElementById('modal-contract-tag').innerText = item.contract_tag;
      document.getElementById('modal-contract-desc').innerText = item.contract_description;
    } else {
      contractBox.classList.add('hidden');
    }
  }

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

// =========================================================================
// MEMBERSHIPS & CANCELLATIONS MODULE (דו״ח ארבוקס + מכירות)
// =========================================================================

function changeMembershipSnapshot(val) {
  currentSnapshot = val;
  fetchDashboardData();
}

function setMembershipsTableTab(tab) {
  currentMembershipsTableTab = tab;
  const btnCancels = document.getElementById('mem-tab-btn-cancels');
  const btnRefunds = document.getElementById('mem-tab-btn-refunds');
  const containerCancels = document.getElementById('mem-table-container-cancels');
  const containerRefunds = document.getElementById('mem-table-container-refunds');

  if (tab === 'cancels') {
    btnCancels.className = 'px-3.5 py-1.5 rounded-xl font-bold text-xs bg-slate-900 text-white shadow-xs transition';
    btnRefunds.className = 'px-3.5 py-1.5 rounded-xl font-medium text-xs text-slate-600 hover:bg-slate-200 transition';
    containerCancels.classList.remove('hidden');
    containerRefunds.classList.add('hidden');
  } else {
    btnRefunds.className = 'px-3.5 py-1.5 rounded-xl font-bold text-xs bg-slate-900 text-white shadow-xs transition';
    btnCancels.className = 'px-3.5 py-1.5 rounded-xl font-medium text-xs text-slate-600 hover:bg-slate-200 transition';
    containerRefunds.classList.remove('hidden');
    containerCancels.classList.add('hidden');
  }
}

function renderMemberships(data) {
  const mem = data.memberships;
  const sales = data.sales_cancellations;
  if (!mem || !mem.stats) return;

  // 1. Populate Snapshot Select
  const monthPill = document.getElementById('mem-active-month-pill');
  if (monthPill && data.metadata) {
    monthPill.innerText = `${data.metadata.month_name} 2026`;
  }

  const snapSelect = document.getElementById('mem-snapshot-select');
  if (snapSelect && mem.available_snapshots && mem.available_snapshots.length > 0) {
    const currentVal = mem.active_tab;
    snapSelect.innerHTML = mem.available_snapshots.map(s => `
      <option value="${s.sheet}" ${s.sheet === currentVal ? 'selected' : ''}>
        ${s.sheet} (${s.label})
      </option>
    `).join('');
  }

  const stats = mem.stats;
  const targetKey = (currentClub === 'all') ? 'all' : currentClub;
  const curStats = stats[targetKey] || stats['all'];
  const gymStats = stats['gym'];
  const pilStats = stats['pilates'];
  const allStats = stats['all'];

  // Total active & percentages
  document.getElementById('mem-kpi-active-total').innerText = curStats.active.toLocaleString('he-IL');
  const totalBase = curStats.active + curStats.frozen + curStats.future_cancellations;
  const activePct = totalBase > 0 ? Math.round((curStats.active / totalBase) * 100) : 100;
  document.getElementById('mem-kpi-active-pct').innerText = `${activePct}% פעילים`;

  document.getElementById('mem-kpi-active-gym').innerText = gymStats.active.toLocaleString('he-IL');
  document.getElementById('mem-kpi-active-pilates').innerText = pilStats.active.toLocaleString('he-IL');

  const gymActivePct = allStats.active > 0 ? (gymStats.active / allStats.active) * 100 : 50;
  const pilActivePct = allStats.active > 0 ? (pilStats.active / allStats.active) * 100 : 50;
  const gymBar = document.getElementById('mem-kpi-active-gym-bar');
  const pilBar = document.getElementById('mem-kpi-active-pilates-bar');
  if (gymBar) gymBar.style.width = `${gymActivePct}%`;
  if (pilBar) pilBar.style.width = `${pilActivePct}%`;

  // Frozen & Pending Freezes
  document.getElementById('mem-kpi-frozen-total').innerText = curStats.frozen.toLocaleString('he-IL');
  const frozenPct = totalBase > 0 ? ((curStats.frozen / totalBase) * 100).toFixed(1) : 0;
  document.getElementById('mem-kpi-frozen-pct').innerText = `${frozenPct}% מסה״כ`;
  document.getElementById('mem-kpi-frozen-gym').innerText = gymStats.frozen.toLocaleString('he-IL');
  document.getElementById('mem-kpi-frozen-pilates').innerText = pilStats.frozen.toLocaleString('he-IL');

  const pendingFreezesEl = document.getElementById('mem-kpi-pending-freezes-count');
  if (pendingFreezesEl) {
    const pFrz = curStats.pending_freezes !== undefined ? curStats.pending_freezes : (mem.pending_freezes || 0);
    pendingFreezesEl.innerText = `${pFrz} ממתינות לטיפול`;
  }

  // Future Cancellations & Pending Cancellations
  document.getElementById('mem-kpi-cancel-total').innerText = curStats.future_cancellations.toLocaleString('he-IL');
  document.getElementById('mem-kpi-cancel-gym').innerText = gymStats.future_cancellations.toLocaleString('he-IL');
  document.getElementById('mem-kpi-cancel-pilates').innerText = pilStats.future_cancellations.toLocaleString('he-IL');

  const pendingCancelsEl = document.getElementById('mem-kpi-pending-cancels-count');
  if (pendingCancelsEl) {
    const pCnc = curStats.pending_cancellations !== undefined ? curStats.pending_cancellations : (mem.pending_cancellations || 0);
    pendingCancelsEl.innerText = `${pCnc} ממתינות לאישור מנהל`;
  }

  // Urgent Customer Alerts Banner (עצבים / חריגים / תלונות חמורות)
  renderUrgentAlertsBanner(mem.urgent_alerts || []);

  // Average Price
  document.getElementById('mem-kpi-avg-price-total').innerText = formatNIS(curStats.avg_price);
  document.getElementById('mem-kpi-avg-price-gym').innerText = formatNIS(gymStats.avg_price);
  document.getElementById('mem-kpi-avg-price-pilates').innerText = formatNIS(pilStats.avg_price);

  // Average Monthly Price
  document.getElementById('mem-kpi-monthly-price-total').innerText = `${formatNIS(curStats.avg_monthly_price)}`;
  document.getElementById('mem-kpi-monthly-price-gym').innerText = `${formatNIS(gymStats.avg_monthly_price)}`;
  document.getElementById('mem-kpi-monthly-price-pilates').innerText = `${formatNIS(pilStats.avg_monthly_price)}`;

  // Sales Refunds Summary (כל הפניות שכרגע ממתינות לקבל עליהן כסף, שאושרו וממתינות לזיכוי)
  if (sales && sales.summary) {
    const sSum = sales.summary;
    document.getElementById('mem-kpi-refund-pending').innerText = formatNIS(sSum.approved_pending_refund_amount);
    document.getElementById('mem-kpi-refund-pending-count').innerText = `${sSum.approved_pending_count || 0} פניות שאושרו וממתינות לזיכוי`;
    document.getElementById('mem-kpi-refund-approved').innerText = formatNIS(sSum.approved_pending_refund_amount);
    document.getElementById('mem-kpi-refund-completed').innerText = formatNIS(sSum.completed_refund_amount);
  }

  // Update Home View Banner Elements (View 1)
  const homeBadge = document.getElementById('home-mem-snapshot-badge');
  const clubLabelText = (currentClub === 'gym') ? 'חדר כושר' : ((currentClub === 'pilates') ? 'פילאטיס' : 'מאוחד');
  if (homeBadge) homeBadge.innerText = `Snapshot ${mem.active_tab || ''} • ${clubLabelText}`;

  const homeActive = document.getElementById('home-mem-active');
  const homeActiveSub = document.getElementById('home-mem-active-sub');
  if (homeActive) homeActive.innerText = curStats.active.toLocaleString('he-IL');
  if (homeActiveSub) {
    if (currentClub === 'gym') {
      homeActiveSub.innerText = `${gymStats.active} מנויי חדר כושר בלבד`;
    } else if (currentClub === 'pilates') {
      homeActiveSub.innerText = `${pilStats.active} מנויי פילאטיס מכשירים בלבד`;
    } else {
      homeActiveSub.innerText = `${gymStats.active} מועדון • ${pilStats.active} פילאטיס`;
    }
  }

  const homeFrozen = document.getElementById('home-mem-frozen');
  const homeFrozenSub = document.getElementById('home-mem-frozen-sub');
  if (homeFrozen) homeFrozen.innerText = curStats.frozen.toLocaleString('he-IL');
  if (homeFrozenSub) {
    if (currentClub === 'gym') {
      homeFrozenSub.innerText = `${gymStats.frozen} מנויי חדר כושר בהקפאה`;
    } else if (currentClub === 'pilates') {
      homeFrozenSub.innerText = `${pilStats.frozen} מנויי פילאטיס בהקפאה`;
    } else {
      homeFrozenSub.innerText = `${gymStats.frozen} מועדון • ${pilStats.frozen} פילאטיס`;
    }
  }

  const homeCancels = document.getElementById('home-mem-cancels');
  const homeCancelsSub = document.getElementById('home-mem-cancels-sub');
  if (homeCancels) homeCancels.innerText = curStats.future_cancellations.toLocaleString('he-IL');
  if (homeCancelsSub) {
    if (currentClub === 'gym') {
      homeCancelsSub.innerText = `${gymStats.future_cancellations} ביטולים בחדר כושר`;
    } else if (currentClub === 'pilates') {
      homeCancelsSub.innerText = `${pilStats.future_cancellations} ביטולים בפילאטיס`;
    } else {
      homeCancelsSub.innerText = `${gymStats.future_cancellations} מועדון • ${pilStats.future_cancellations} פילאטיס`;
    }
  }

  const homeRefund = document.getElementById('home-mem-refund');
  if (homeRefund && sales && sales.summary) {
    homeRefund.innerText = formatNIS(sales.summary.approved_pending_refund_amount);
  }

  // Render Charts & Analytics
  if (currentView === 'memberships') {
    try {
      renderMembershipCharts(mem);
      renderNewJoinsChart(mem.new_joins_timeline || []);
      renderSeasonalMembershipChart(mem.seasonal_trends);
    } catch (err) {
      console.warn('Membership charts warning:', err);
    }
  }

  // Always render refund forecast grid from Drive sheet
  renderRefundForecastGrid(mem.monthly_refund_forecast || []);

  // Render Analytics Cards & Cohorts
  filterMemTypes(currentMemTypeClub);
  filterReasonsPeriod(currentReasonPeriod);
  renderExpiringCohorts(mem.expiring_memberships || []);
  renderSalesClosersList(sales ? (sales.sales_closers || []) : [], data.metadata ? data.metadata.month_name : 'יוני');
}

function renderUrgentAlertsBanner(alerts) {
  const container = document.getElementById('mem-urgent-alert-banner');
  if (!container) return;

  if (!alerts || alerts.length === 0) {
    container.classList.add('hidden');
    container.innerHTML = '';
    return;
  }

  container.classList.remove('hidden');
  const topAlerts = alerts.slice(0, 3); // show up to 3 most critical

  container.innerHTML = `
    <div class="relative overflow-hidden rounded-2xl bg-gradient-to-r from-rose-600 via-rose-700 to-red-800 text-white p-5 shadow-xl border-2 border-rose-500 animate-pulse-subtle">
      <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/20 pb-3 mb-4">
        <div class="flex items-center gap-3">
          <div class="w-12 h-12 rounded-xl bg-white/20 backdrop-blur-md flex items-center justify-center text-white text-2xl shadow-inner border border-white/30 shrink-0">
            🚨
          </div>
          <div>
            <div class="flex items-center gap-2">
              <h3 class="text-lg font-black tracking-tight text-white">התראת שירות חריגה: לקוחות כועסים / פניות דחופות בטיפול</h3>
              <span class="px-2.5 py-0.5 text-xs font-black bg-white text-rose-800 rounded-full shadow-sm">
                ${alerts.length} מקרים חריגים זוהו
              </span>
            </div>
            <p class="text-xs text-rose-100 font-medium mt-0.5">
              מערכת הניטור זיהתה מילות מפתח המעידות על לקוח נסער (עו״ד, תביעות, ציוד תקול, טענות עיכוב ביטול ממזמן)
            </p>
          </div>
        </div>
        <div class="text-xs font-bold bg-black/30 backdrop-blur-md px-3 py-1.5 rounded-xl border border-white/20 text-rose-100 shrink-0">
          דורש התערבות מיידית של מנהל המועדון
        </div>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
        ${topAlerts.map(a => `
          <div class="bg-white/10 hover:bg-white/15 transition backdrop-blur-sm rounded-xl p-3.5 border border-white/20 flex flex-col justify-between space-y-2">
            <div>
              <div class="flex items-center justify-between gap-1 mb-1.5">
                <span class="font-black text-sm text-white flex items-center gap-1.5">
                  <span class="w-2 h-2 rounded-full bg-amber-400"></span>
                  ${a.name}
                </span>
                <span class="text-[10px] font-extrabold px-2 py-0.5 rounded bg-rose-950/80 text-rose-200 border border-rose-500/40">
                  ${a.req_type}
                </span>
              </div>
              <div class="text-xs text-rose-100 line-clamp-3 font-normal leading-relaxed bg-black/20 p-2 rounded-lg border border-white/10">
                "${a.notes}"
              </div>
            </div>
            <div class="pt-2 border-t border-white/10 flex items-center justify-between text-[11px] text-rose-200">
              <span class="truncate max-w-[120px]">נציג: ${a.opener || 'נציג שירות'}</span>
              <span class="font-bold text-amber-300 bg-amber-950/60 px-2 py-0.5 rounded border border-amber-500/30">${a.status}</span>
            </div>
          </div>
        `).join('')}
      </div>
    </div>
  `;
  if (window.lucide) lucide.createIcons();
}

// -------------------------------------------------------------------------
// MEMBERSHIP TYPES FILTER & RENDER
// -------------------------------------------------------------------------
function filterMemTypes(club) {
  currentMemTypeClub = club;
  ['all', 'gym', 'pilates'].forEach(c => {
    const btn = document.getElementById(`mem-type-tab-${c}`);
    if (btn) {
      if (c === club) {
        btn.className = 'px-2.5 py-1 rounded-lg bg-white text-slate-900 shadow-2xs font-bold';
      } else {
        btn.className = 'px-2.5 py-1 rounded-lg hover:text-slate-900 font-semibold';
      }
    }
  });

  if (!dashboardData || !dashboardData.memberships) return;
  const mem = dashboardData.memberships;
  let types = mem.membership_types || [];
  if (mem.membership_types_by_club && mem.membership_types_by_club[club]) {
    types = mem.membership_types_by_club[club];
  }
  renderMembershipTypesList(types);
}

function renderMembershipTypesList(types) {
  const container = document.getElementById('mem-types-list');
  if (!container) return;
  if (!types || types.length === 0) {
    container.innerHTML = '<div class="text-center py-4 text-slate-400 text-xs">אין נתוני מנויים</div>';
    return;
  }
  container.innerHTML = types.map(t => `
    <div class="space-y-1">
      <div class="flex justify-between items-center text-xs">
        <span class="font-medium text-slate-700 truncate max-w-[200px]" title="${t.name}">${t.name}</span>
        <div class="flex items-center gap-2">
          <span class="font-bold text-slate-900">${t.count} מנויים</span>
          <span class="text-[10px] font-semibold text-indigo-600 bg-indigo-50 px-1.5 py-0.5 rounded">${t.pct}%</span>
        </div>
      </div>
      <div class="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden">
        <div class="bg-indigo-600 h-full rounded-full transition-all duration-500" style="width: ${Math.min(t.pct * 2.5, 100)}%"></div>
      </div>
    </div>
  `).join('');
}

// -------------------------------------------------------------------------
// REASONS BREAKDOWN FILTER & RENDER
// -------------------------------------------------------------------------
function filterReasonsPeriod(period) {
  currentReasonPeriod = period;
  ['1m', '3m', '1y', 'all'].forEach(p => {
    const btn = document.getElementById(`reason-tab-${p}`);
    if (btn) {
      if (p === period) {
        btn.className = 'px-2 py-1 rounded-lg bg-white text-slate-900 shadow-2xs font-bold';
      } else {
        btn.className = 'px-2 py-1 rounded-lg hover:text-slate-900 font-semibold';
      }
    }
  });

  if (!dashboardData || !dashboardData.sales_cancellations) return;
  const sales = dashboardData.sales_cancellations;
  let reasons = sales.reasons_breakdown || [];
  if (sales.reasons_by_period && sales.reasons_by_period[period]) {
    reasons = sales.reasons_by_period[period];
  }
  renderReasonsList(reasons);
}

function renderReasonsList(reasons) {
  const container = document.getElementById('mem-reasons-list');
  if (!container) return;
  if (!reasons || reasons.length === 0) {
    container.innerHTML = '<div class="text-center py-4 text-slate-400 text-xs">אין נתוני סיבות לתקופה זו</div>';
    return;
  }
  const colorMap = {
    'חו״ל וחופשות': 'bg-blue-500',
    'רפואי ובריאותי': 'bg-rose-500',
    'חוסר זמן / עומס': 'bg-amber-500',
    'מעבר דירה ומגורים': 'bg-purple-500',
    'שירות צבאי ומילואים': 'bg-emerald-500',
    'שיקול כלכלי ומחיר': 'bg-cyan-500',
    'אחר / שונות': 'bg-slate-400'
  };
  container.innerHTML = reasons.map(r => `
    <div class="space-y-1">
      <div class="flex justify-between items-center text-xs">
        <span class="font-medium text-slate-700">${r.reason}</span>
        <div class="flex items-center gap-1.5">
          <span class="font-bold text-slate-900">${r.count} פניות</span>
          <span class="text-[10px] text-slate-400">(${r.pct}%)</span>
        </div>
      </div>
      <div class="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden">
        <div class="${colorMap[r.reason] || 'bg-blue-500'} h-full rounded-full transition-all duration-500" style="width: ${Math.min(r.pct * 2.2, 100)}%"></div>
      </div>
    </div>
  `).join('');
}

// -------------------------------------------------------------------------
// SEASONAL MEMBERSHIP TRENDS EVOLUTION (AREA CHART)
// -------------------------------------------------------------------------
// -------------------------------------------------------------------------
// QUARTERLY MEMBERSHIP TRENDS EVOLUTION (Q1–Q4 & MULTI-YEAR)
// -------------------------------------------------------------------------
let currentQuarterlyYear = '2026';
let cachedSeasonalData = null;

function selectQuarterlyYear(year) {
  currentQuarterlyYear = year;
  
  // Update button active styles
  const buttons = document.querySelectorAll('.quarterly-year-btn');
  buttons.forEach(btn => {
    const bYear = btn.getAttribute('data-year');
    if (bYear === year) {
      btn.className = 'quarterly-year-btn px-3 py-1 rounded-lg transition-all bg-white text-slate-900 shadow-xs border border-slate-200';
    } else {
      btn.className = 'quarterly-year-btn px-3 py-1 rounded-lg transition-all text-slate-500 hover:text-slate-900';
    }
  });

  if (cachedSeasonalData) {
    renderQuarterlyMembershipTable(cachedSeasonalData, year);
  }
}
window.selectQuarterlyYear = selectQuarterlyYear;

function renderSeasonalMembershipChart(seasonal) {
  renderQuarterlyMembershipTable(seasonal, currentQuarterlyYear);
}

function renderQuarterlyMembershipTable(seasonal, selectedYear) {
  if (!seasonal) return;
  cachedSeasonalData = seasonal;
  if (!selectedYear) selectedYear = currentQuarterlyYear || '2026';

  // Destroy legacy chart if present
  if (chartSeasonalMem) {
    try { chartSeasonalMem.destroy(); } catch (e) {}
    chartSeasonalMem = null;
  }

  const thead = document.getElementById('mem-quarterly-table-header');
  const tbody = document.getElementById('mem-quarterly-table-body');
  const tfoot = document.getElementById('mem-quarterly-table-footer');
  const noteEl = document.getElementById('quarterly-active-note');
  if (!tbody) return;

  const byYear = seasonal.quarterly_by_year || {};
  const defaultColors = ['#4f46e5', '#06b6d4', '#10b981', '#f59e0b', '#ec4899', '#8b5cf6'];

  if (selectedYear === 'compare') {
    // Multi-Year Comparison Mode (Year-over-Year / שנה פר שנה)
    if (noteEl) noteEl.innerText = '*השוואה שנתית רוחבית: ביצוע 2025, ביצוע וצפי 2026 ויעד אסטרטגי 2027';

    if (thead) {
      thead.innerHTML = `
        <tr class="bg-slate-50 text-slate-500 font-bold border-b border-slate-200">
          <th class="py-2 px-2.5 rounded-r-lg">סוג מנוי מוביל</th>
          <th class="py-2 px-2 text-center">2025 (היסטוריה)</th>
          <th class="py-2 px-2 text-center bg-indigo-50/60 text-indigo-900 font-black">2026 (נוכחית 🎯)</th>
          <th class="py-2 px-2 text-center bg-purple-50/60 text-purple-900 font-black">2027 (צפי 🔮)</th>
          <th class="py-2 px-2 text-center">צמיחה שנתית (YoY)</th>
          <th class="py-2 px-2 rounded-l-lg">תובנה אסטרטגית ומגמה</th>
        </tr>
      `;
    }

    const y25 = byYear['2025'] || {};
    const y26 = byYear['2026'] || {};
    const y27 = byYear['2027'] || {};

    const rows26 = y26.rows || seasonal.quarterly_table || [];
    tbody.innerHTML = rows26.map((r26, idx) => {
      const r25 = (y25.rows || []).find(r => r.name === r26.name) || {};
      const r27 = (y27.rows || []).find(r => r.name === r26.name) || {};
      const color = r26.color || defaultColors[idx % defaultColors.length];

      const v25 = r25.annual_avg || r25.q4 || '-';
      const v26 = r26.annual_avg || r26.q3 || '-';
      const v27 = r27.annual_avg || r27.q4 || '-';

      const growth = r26.delta_str || '+10%';
      const isGrowth = growth.includes('+') || growth.includes('זינוק');
      const badgeClass = isGrowth
        ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
        : (growth === 'עונתי' ? 'bg-amber-50 text-amber-700 border-amber-200' : 'bg-slate-50 text-slate-600 border-slate-200');

      return `
        <tr class="hover:bg-slate-50/80 transition-colors">
          <td class="py-2 px-2.5 font-bold text-slate-800 flex items-center gap-1.5">
            <span class="w-2 h-2 rounded-full" style="background-color: ${color}"></span>
            ${r26.name}
          </td>
          <td class="py-2 px-2 text-center text-slate-600 font-semibold">${v25}</td>
          <td class="py-2 px-2 text-center font-black text-indigo-900 bg-indigo-50/40">${v26}</td>
          <td class="py-2 px-2 text-center font-black text-purple-900 bg-purple-50/40">${v27}</td>
          <td class="py-2 px-2 text-center">
            <span class="px-2 py-0.5 rounded-full text-[10px] font-black border ${badgeClass}">
              ${growth}
            </span>
          </td>
          <td class="py-2 px-2 text-[10.5px] text-slate-500">
            <span class="font-semibold text-slate-700">${r26.trend_badge || ''}</span>
            <span class="text-slate-400 block text-[9.5px]">${r26.note || ''}</span>
          </td>
        </tr>
      `;
    }).join('');

    if (tfoot) {
      const tot25 = (y25.totals ? y25.totals.annual_avg : 726);
      const tot26 = (y26.totals ? y26.totals.q3 : 852);
      const tot27 = (y27.totals ? y27.totals.annual_avg : 934);

      tfoot.innerHTML = `
        <tr class="bg-slate-100/70 font-black text-slate-900 border-t-2 border-slate-300">
          <td class="py-2 px-2.5 rounded-r-lg">סה״כ מנויים פעילים (ממוצע/שיא)</td>
          <td class="py-2 px-2 text-center text-slate-600">${tot25} מנויים</td>
          <td class="py-2 px-2 text-center bg-indigo-100/50 text-indigo-900 font-black">${tot26} מנויים</td>
          <td class="py-2 px-2 text-center bg-purple-100/50 text-purple-900 font-black">${tot27} מנויים</td>
          <td class="py-2 px-2 text-center text-emerald-600">+11.0%</td>
          <td class="py-2 px-2 rounded-l-lg text-[10px] text-slate-500 font-normal">צמיחה רב-שנתית עקבית במועדון A+ ובפילאטיס</td>
        </tr>
      `;
    }

  } else {
    // Single Year Mode (Q1, Q2, Q3, Q4)
    const yData = byYear[selectedYear] || byYear['2026'] || {};
    const rows = yData.rows || seasonal.quarterly_table || [];
    const totals = yData.totals || {};

    if (noteEl) {
      if (selectedYear === '2026') {
        noteEl.innerText = '*2026: ביצוע מאומת Q1–Q3 וצפי סגירה אסטרטגי Q4';
      } else if (selectedYear === '2025') {
        noteEl.innerText = '*2025: נתוני ביצוע היסטוריים מאומתים מסגירת שנת 2025';
      } else {
        noteEl.innerText = '*2027: תחזית אסטרטגית ויעדי התרחבות תפוסה';
      }
    }

    if (thead) {
      const isCurrent26 = selectedYear === '2026';
      thead.innerHTML = `
        <tr class="bg-slate-50 text-slate-500 font-bold border-b border-slate-200">
          <th class="py-2 px-2.5 rounded-r-lg">סוג מנוי מוביל</th>
          <th class="py-2 px-2 text-center">Q1 (ינו-מרץ)</th>
          <th class="py-2 px-2 text-center">Q2 (אפר-יוני)</th>
          <th class="py-2 px-2 text-center ${isCurrent26 ? 'bg-indigo-50/60 text-indigo-900 font-black' : ''}">Q3 (יול-ספט) ${isCurrent26 ? '🎯' : ''}</th>
          <th class="py-2 px-2 text-center ${isCurrent26 ? 'bg-purple-50/60 text-purple-900 font-black' : ''}">Q4 (אוק-דצמ) ${isCurrent26 ? '🔮' : ''}</th>
          <th class="py-2 px-2 text-center">ממוצע שנתי</th>
          <th class="py-2 px-2 text-center">קצב שינוי</th>
          <th class="py-2 px-2 rounded-l-lg">תובנה ניהולית ומגמה</th>
        </tr>
      `;
    }

    tbody.innerHTML = rows.map((row, idx) => {
      const isGrowth = (row.delta_str || '').includes('+') || (row.delta_str || '').includes('זינוק');
      const badgeClass = isGrowth
        ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
        : (row.delta_str === 'עונתי' ? 'bg-amber-50 text-amber-700 border-amber-200' : 'bg-slate-50 text-slate-600 border-slate-200');
      const color = row.color || defaultColors[idx % defaultColors.length];

      return `
        <tr class="hover:bg-slate-50/80 transition-colors">
          <td class="py-2 px-2.5 font-bold text-slate-800 flex items-center gap-1.5">
            <span class="w-2 h-2 rounded-full" style="background-color: ${color}"></span>
            ${row.name}
          </td>
          <td class="py-2 px-2 text-center text-slate-600 font-semibold">${row.q1}</td>
          <td class="py-2 px-2 text-center text-slate-600 font-semibold">${row.q2}</td>
          <td class="py-2 px-2 text-center font-black text-indigo-900 bg-indigo-50/40">${row.q3}</td>
          <td class="py-2 px-2 text-center font-black text-purple-900 bg-purple-50/40">${row.q4}</td>
          <td class="py-2 px-2 text-center text-slate-700 font-bold bg-slate-50/40">${row.annual_avg || Math.round((row.q1+row.q2+row.q3+row.q4)/4)}</td>
          <td class="py-2 px-2 text-center">
            <span class="px-2 py-0.5 rounded-full text-[10px] font-black border ${badgeClass}">
              ${row.delta_str}
            </span>
          </td>
          <td class="py-2 px-2 text-[10.5px] text-slate-500">
            <span class="font-semibold text-slate-700">${row.trend_badge || ''}</span>
            <span class="text-slate-400 block text-[9.5px]">${row.note || ''}</span>
          </td>
        </tr>
      `;
    }).join('');

    if (tfoot) {
      const q1Tot = totals.q1 || 788;
      const q2Tot = totals.q2 || 796;
      const q3Tot = totals.q3 || 852;
      const q4Tot = totals.q4 || 875;
      const avgTot = totals.annual_avg || 828;
      const growthTot = totals.growth || '+11.0%';
      const noteTot = totals.note || 'צמיחה שנתית עקבית במועדון ובפילאטיס';

      tfoot.innerHTML = `
        <tr class="bg-slate-100/70 font-black text-slate-900 border-t-2 border-slate-300">
          <td class="py-2 px-2.5 rounded-r-lg">סה״כ מנויים פעילים במועדון</td>
          <td class="py-2 px-2 text-center">${q1Tot}</td>
          <td class="py-2 px-2 text-center">${q2Tot}</td>
          <td class="py-2 px-2 text-center bg-indigo-100/50 text-indigo-900 font-black">${q3Tot}</td>
          <td class="py-2 px-2 text-center bg-purple-100/50 text-purple-900 font-black">${q4Tot}</td>
          <td class="py-2 px-2 text-center bg-slate-200/50 text-slate-900 font-black">${avgTot}</td>
          <td class="py-2 px-2 text-center text-emerald-600">${growthTot}</td>
          <td class="py-2 px-2 rounded-l-lg text-[10px] text-slate-500 font-normal">${noteTot}</td>
        </tr>
      `;
    }
  }
}

// -------------------------------------------------------------------------
// UPCOMING EXPIRING MEMBERSHIPS COHORTS
// -------------------------------------------------------------------------
function renderExpiringCohorts(members) {
  const badgeEl = document.getElementById('mem-expiring-total-badge');
  const pillsContainer = document.getElementById('mem-expiring-month-pills');
  const tableBody = document.getElementById('mem-expiring-table-body');
  if (!pillsContainer || !tableBody) return;

  if (badgeEl) {
    badgeEl.innerText = `${members.length} מנויים לסיום`;
  }

  if (!members || members.length === 0) {
    pillsContainer.innerHTML = '';
    tableBody.innerHTML = '<tr><td colspan="4" class="text-center py-6 text-slate-400">אין מנויים שעומדים להסתיים</td></tr>';
    return;
  }

  // Group by month
  const byMonth = {};
  members.forEach(m => {
    const mo = m.month || '2026-09';
    if (!byMonth[mo]) byMonth[mo] = [];
    byMonth[mo].push(m);
  });

  const sortedMonths = Object.keys(byMonth).sort();
  if (!currentExpiringMonth || !byMonth[currentExpiringMonth]) {
    currentExpiringMonth = sortedMonths[0];
  }

  // Render Month Pills
  pillsContainer.innerHTML = sortedMonths.map(mo => {
    const [yr, mNum] = mo.split('-');
    const label = `${MONTH_NAMES[parseInt(mNum) - 1]} ${yr}`;
    const isAct = (mo === currentExpiringMonth);
    return `
      <button onclick="selectExpiringCohort('${mo}')" class="px-3 py-1.5 rounded-xl transition whitespace-nowrap flex items-center gap-1.5 ${isAct ? 'bg-amber-500 text-white font-black shadow-xs' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}">
        <span>${label}</span>
        <span class="px-1.5 py-0.2 text-[10px] rounded-full ${isAct ? 'bg-amber-700 text-amber-100' : 'bg-slate-200 text-slate-700'}">${byMonth[mo].length}</span>
      </button>
    `;
  }).join('');

  // Render Active Month Table Rows - sorted by end date ascending
  const cohortList = (byMonth[currentExpiringMonth] || []).slice();
  cohortList.sort((a, b) => (a.raw_date || a.end_date).localeCompare(b.raw_date || b.end_date));

  tableBody.innerHTML = cohortList.map(item => {
    const isHighRisk = (item.persistence_risk === 'high');
    const isMedRisk = (item.persistence_risk === 'medium');

    let standardBadge = '';
    if (isHighRisk) {
      standardBadge = `<span class="px-2.5 py-1 rounded-lg text-[11px] font-black bg-rose-100 text-rose-800 border border-rose-200 inline-flex items-center gap-1.5 whitespace-nowrap shadow-2xs"><i data-lucide="alert-triangle" class="w-3.5 h-3.5 text-rose-600 shrink-0"></i> ${item.persistence_label}</span>`;
    } else if (isMedRisk) {
      standardBadge = `<span class="px-2.5 py-1 rounded-lg text-[11px] font-bold bg-amber-50 text-amber-800 border border-amber-200 inline-flex items-center gap-1.5 whitespace-nowrap"><i data-lucide="clock" class="w-3.5 h-3.5 text-amber-600 shrink-0"></i> ${item.persistence_label}</span>`;
    } else {
      standardBadge = `<span class="px-2.5 py-1 rounded-lg text-[11px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200 inline-flex items-center gap-1.5 whitespace-nowrap"><i data-lucide="check" class="w-3.5 h-3.5 text-emerald-600 shrink-0"></i> ${item.persistence_label}</span>`;
    }

    let attDisplay = '';
    if (item.has_real_attendance) {
      attDisplay = `<span class="font-bold text-slate-800 whitespace-nowrap">${item.visits_str}</span>`;
    } else {
      attDisplay = `<span class="text-slate-400 text-[11px] inline-flex items-center justify-center gap-1 whitespace-nowrap" title="ניתן לגרור דוח התמדה מ-Arbox לנתוני אמת"><i data-lucide="activity" class="w-3.5 h-3.5 text-amber-500 shrink-0"></i> ${item.visits_str}</span>`;
    }

    const rowClass = isHighRisk
      ? 'bg-rose-50/70 hover:bg-rose-100/70 border-r-4 border-r-rose-500 font-medium transition'
      : (isMedRisk ? 'hover:bg-amber-50/40 transition' : 'hover:bg-slate-50/80 transition');

    return `
      <tr class="${rowClass}">
        <td class="py-2.5 px-3.5 font-bold whitespace-nowrap ${isHighRisk ? 'text-rose-950 font-black' : 'text-slate-900'}">${item.name}</td>
        <td class="py-2.5 px-3 text-slate-700 whitespace-nowrap">${item.membership}</td>
        <td class="py-2.5 px-3 text-center whitespace-nowrap">
          <span class="px-2.5 py-0.5 rounded-md text-[11px] font-bold ${item.branch_key === 'pilates' ? 'bg-purple-50 text-purple-700 border border-purple-200/60' : 'bg-blue-50 text-blue-700 border border-blue-200/60'}">
            ${item.branch}
          </span>
        </td>
        <td class="py-2.5 px-3 text-center text-xs whitespace-nowrap">${attDisplay}</td>
        <td class="py-2.5 px-3 whitespace-nowrap">${standardBadge}</td>
        <td class="py-2.5 px-4 text-left font-mono font-black text-xs whitespace-nowrap ${isHighRisk ? 'text-rose-700' : 'text-amber-700'}">${item.end_date}</td>
      </tr>
    `;
  }).join('');
  if (window.lucide) lucide.createIcons();
}

function selectExpiringCohort(monthKey) {
  currentExpiringMonth = monthKey;
  if (dashboardData && dashboardData.memberships) {
    renderExpiringCohorts(dashboardData.memberships.expiring_memberships || []);
  }
}

function renderNewJoinsChart(timeline) {
  const el = document.getElementById('mem-joins-chart');
  if (!el || !timeline || timeline.length === 0) return;
  el.innerHTML = '';
  const options = {
    series: [{
      name: 'מצטרפים חדשים',
      data: timeline.map(x => x.count)
    }],
    chart: {
      type: 'area',
      height: 200,
      fontFamily: 'Heebo, sans-serif',
      toolbar: { show: false }
    },
    colors: ['#10b981'],
    fill: {
      type: 'gradient',
      gradient: {
        shadeIntensity: 1,
        opacityFrom: 0.45,
        opacityTo: 0.05,
        stops: [20, 100]
      }
    },
    stroke: { curve: 'smooth', width: 2.5 },
    xaxis: {
      categories: timeline.map(x => x.label),
      labels: { style: { colors: '#64748b', fontWeight: 600 } }
    },
    yaxis: {
      labels: { style: { colors: '#64748b' } }
    },
    dataLabels: { enabled: true, offsetY: -5, style: { fontSize: '10px', colors: ['#059669'] } }
  };
  if (chartMemJoins) {
    try { chartMemJoins.destroy(); } catch (e) {}
  }
  chartMemJoins = new ApexCharts(el, options);
  chartMemJoins.render();
}

function renderSalesClosersList(closers, monthName) {
  const container = document.getElementById('sales-closers-list');
  const labelEl = document.getElementById('sales-closers-month-label');
  if (labelEl) labelEl.innerText = `חודש ${monthName} 2026`;
  if (!container) return;
  if (!closers || closers.length === 0) {
    container.innerHTML = '<div class="text-center py-4 text-zinc-400 text-xs">אין נתוני סגירות לחודש זה</div>';
    return;
  }
  container.innerHTML = closers.map((c, idx) => `
    <div class="flex items-center justify-between p-2.5 rounded-xl bg-zinc-50 border border-zinc-200/70">
      <div class="flex items-center gap-2.5">
        <div class="w-6 h-6 rounded-lg ${idx === 0 ? 'bg-rose-600 text-white' : 'bg-zinc-200 text-zinc-800'} font-black text-xs flex items-center justify-center shadow-2xs">
          ${idx + 1}
        </div>
        <div>
          <div class="text-xs font-bold text-zinc-900">${c.name}</div>
          <div class="text-[10px] text-zinc-400 font-medium">${c.leads} לידים שטופלו</div>
        </div>
      </div>
      <div class="text-left">
        <div class="text-xs font-black text-emerald-600">${c.closings} סגירות</div>
        <div class="text-[10px] font-black text-zinc-700">${formatNIS(c.total_amount)}</div>
      </div>
    </div>
  `).join('');
}

function renderMembershipCharts(mem) {
  if (!mem || !mem.stats) return;
  const gym = mem.stats.gym;
  const pil = mem.stats.pilates;

  // Chart 1: Distribution
  const distEl = document.getElementById('mem-distribution-chart');
  if (distEl) {
    distEl.innerHTML = '';
    const distOptions = {
      series: [
        { name: 'פעיל', data: [gym.active, pil.active] },
        { name: 'הוקפא', data: [gym.frozen, pil.frozen] },
        { name: 'ביטול עתידי', data: [gym.future_cancellations, pil.future_cancellations] }
      ],
      chart: {
        type: 'bar',
        height: 250,
        stacked: true,
        fontFamily: 'Heebo, sans-serif',
        toolbar: { show: false }
      },
      colors: ['#10b981', '#f59e0b', '#e11d48'],
      plotOptions: {
        bar: {
          horizontal: false,
          borderRadius: 6,
          columnWidth: '45%'
        }
      },
      xaxis: {
        categories: ['מועדון A+', 'פילאטיס מכשירים'],
        labels: { style: { colors: '#27272a', fontWeight: 600 } }
      },
      yaxis: {
        labels: { style: { colors: '#71717a' } }
      },
      legend: {
        position: 'top',
        horizontalAlign: 'right',
        fontFamily: 'Heebo'
      },
      dataLabels: { enabled: true }
    };
    if (chartMemDist) {
      try { chartMemDist.destroy(); } catch (e) {}
    }
    chartMemDist = new ApexCharts(distEl, distOptions);
    chartMemDist.render();
  }

  // Chart 2: Timeline of Cancellations & Monthly Refund Forecast
  renderCancellationsTimelineChart(mem);

  // Executive Monthly Refund Schedule Panel (לוח צפי החזרים חודשי מהדרייב)
  renderRefundForecastGrid(mem.monthly_refund_forecast || []);
}

let currentCancelChartMode = 'refund'; // 'refund' | 'count' | 'combined'

function switchCancellationsChartMode(mode) {
  currentCancelChartMode = mode;

  const btnRefund = document.getElementById('btn-cancel-mode-refund');
  const btnCount = document.getElementById('btn-cancel-mode-count');
  const btnCombined = document.getElementById('btn-cancel-mode-combined');

  [btnRefund, btnCount, btnCombined].forEach(btn => {
    if (btn) {
      btn.className = 'px-2.5 py-1 rounded-lg hover:text-slate-900 transition';
    }
  });

  const activeBtn = mode === 'refund' ? btnRefund : (mode === 'count' ? btnCount : btnCombined);
  if (activeBtn) {
    activeBtn.className = 'px-2.5 py-1 rounded-lg bg-white text-slate-900 shadow-2xs font-bold';
  }

  if (dashboardData && dashboardData.memberships) {
    renderCancellationsTimelineChart(dashboardData.memberships);
  }
}

function renderCancellationsTimelineChart(mem) {
  const timeEl = document.getElementById('mem-cancellations-timeline-chart');
  if (!timeEl || !mem) return;

  const forecast = mem.monthly_refund_forecast || [];
  const validForecast = forecast.filter(x => !x.is_total);
  const cancByMonth = mem.cancellations_by_month || [];

  timeEl.innerHTML = '';

  let series = [];
  let categories = [];
  let yaxis = {};
  let colors = [];
  let plotOptions = {};
  let tooltip = {};

  if (currentCancelChartMode === 'refund') {
    if (validForecast.length > 0) {
      categories = validForecast.map(x => x.month);
      series = [{
        name: 'צפי החזר חודשי (₪)',
        type: 'column',
        data: validForecast.map(x => x.amount)
      }];
      colors = ['#e11d48'];
      plotOptions = {
        bar: {
          borderRadius: 6,
          columnWidth: '42%'
        }
      };
      yaxis = {
        labels: {
          style: { colors: '#64748b' },
          formatter: (val) => formatNIS(val)
        }
      };
      tooltip = {
        y: {
          formatter: (val, opt) => {
            const item = validForecast[opt.dataPointIndex];
            if (!item) return formatNIS(val);
            return `${formatNIS(val)} (${item.count} זיכויים • אשראי: ${formatNIS(item.credit_card)} | בנק: ${formatNIS(item.bank_transfer)})`;
          }
        }
      };
    } else {
      categories = cancByMonth.map(x => x.month);
      series = [{ name: 'ביטולים מתוכננים', type: 'column', data: cancByMonth.map(x => x.count) }];
      colors = ['#e11d48'];
      plotOptions = { bar: { borderRadius: 6, columnWidth: '40%' } };
      yaxis = { labels: { style: { colors: '#64748b' } } };
    }
  } else if (currentCancelChartMode === 'count') {
    categories = cancByMonth.map(x => x.month);
    series = [{
      name: 'כמות ביטולים מתוכננים',
      type: 'column',
      data: cancByMonth.map(x => x.count)
    }];
    colors = ['#e11d48'];
    plotOptions = {
      bar: {
        borderRadius: 6,
        columnWidth: '40%'
      }
    };
    yaxis = {
      labels: {
        style: { colors: '#64748b' },
        formatter: (val) => `${Math.round(val)} מבוטלים`
      }
    };
  } else {
    // 'combined' mode: Combo Chart (Column for Refund ₪ + Line for Active Credits count)
    if (validForecast.length > 0) {
      categories = validForecast.map(x => x.month);
      series = [
        {
          name: 'צפי החזר חודשי (₪)',
          type: 'column',
          data: validForecast.map(x => x.amount)
        },
        {
          name: 'כמות זיכויים פעילים',
          type: 'line',
          data: validForecast.map(x => x.count)
        }
      ];
      colors = ['#e11d48', '#4f46e5'];
      plotOptions = {
        bar: {
          borderRadius: 6,
          columnWidth: '40%'
        }
      };
      yaxis = [
        {
          title: { text: 'סכום החזר (₪)', style: { color: '#e11d48', fontSize: '11px', fontWeight: 600 } },
          labels: {
            style: { colors: '#e11d48' },
            formatter: (val) => formatNIS(val)
          }
        },
        {
          opposite: true,
          title: { text: 'כמות זיכויים', style: { color: '#4f46e5', fontSize: '11px', fontWeight: 600 } },
          labels: {
            style: { colors: '#4f46e5' },
            formatter: (val) => `${Math.round(val)}`
          }
        }
      ];
      tooltip = {
        y: {
          formatter: (val, opt) => {
            if (opt.seriesIndex === 0) {
              const item = validForecast[opt.dataPointIndex];
              return `${formatNIS(val)} ${item ? `(אשראי: ${formatNIS(item.credit_card)} | בנק: ${formatNIS(item.bank_transfer)})` : ''}`;
            }
            return `${Math.round(val)} זיכויים`;
          }
        }
      };
    }
  }

  const timeOptions = {
    series: series,
    chart: {
      height: 250,
      type: currentCancelChartMode === 'combined' ? 'line' : 'bar',
      fontFamily: 'Heebo, sans-serif',
      toolbar: { show: false }
    },
    plotOptions: plotOptions,
    colors: colors,
    xaxis: {
      categories: categories,
      labels: { style: { colors: '#475569', fontWeight: 600 } }
    },
    yaxis: yaxis,
    dataLabels: {
      enabled: true,
      offsetY: -5,
      formatter: function(val, opt) {
        if (currentCancelChartMode === 'refund' || (currentCancelChartMode === 'combined' && opt.seriesIndex === 0)) {
          return formatNIS(val);
        }
        return val;
      },
      style: { fontSize: '10px', fontWeight: 'bold' }
    },
    tooltip: tooltip,
    stroke: {
      width: currentCancelChartMode === 'combined' ? [0, 3] : [0],
      curve: 'smooth'
    }
  };

  if (chartMemTimeline) {
    try { chartMemTimeline.destroy(); } catch (e) {}
  }
  chartMemTimeline = new ApexCharts(timeEl, timeOptions);
  chartMemTimeline.render();
}

function renderRefundForecastGrid(forecast) {
  const grid = document.getElementById('refund-forecast-cards-grid');
  const totalBadge = document.getElementById('refund-forecast-total-badge');
  if (!grid) return;

  const items = (forecast || []).filter(x => !x.is_total);
  const totalItem = (forecast || []).find(x => x.is_total);

  if (totalBadge && totalItem) {
    totalBadge.innerHTML = `
      <i data-lucide="coins" class="w-3.5 h-3.5 text-rose-400"></i>
      <span>סה״כ צפי החזרים: ${formatNIS(totalItem.amount)} (${totalItem.count} זיכויים פעילים)</span>
    `;
  }

  if (items.length === 0) {
    grid.innerHTML = '<div class="col-span-4 text-center py-4 text-slate-400 text-xs">אין נתוני צפי החזרים לחודש זה</div>';
    return;
  }

  grid.innerHTML = items.map(item => `
    <div class="bg-slate-50/90 rounded-2xl p-4 border border-slate-200/90 space-y-2.5 hover:shadow-xs transition">
      <div class="flex items-center justify-between">
        <span class="text-xs font-black text-slate-900">${item.month}</span>
        <span class="text-[10px] font-bold px-2 py-0.5 rounded-full bg-rose-100 text-rose-700 border border-rose-200">
          ${item.count} זיכויים
        </span>
      </div>
      
      <div>
        <div class="text-lg font-black text-rose-600">${formatNIS(item.amount)}</div>
        <div class="text-[10px] text-slate-400 font-medium">${item.timing || 'פירעון חודשי'}</div>
      </div>

      <div class="pt-2 border-t border-slate-200/80 space-y-1 text-[11px]">
        <div class="flex justify-between text-slate-600 font-medium">
          <span class="flex items-center gap-1">
            <i data-lucide="credit-card" class="w-3 h-3 text-slate-400"></i>
            אשראי:
          </span>
          <span class="font-bold text-slate-800">${formatNIS(item.credit_card)}</span>
        </div>
        <div class="flex justify-between text-slate-600 font-medium">
          <span class="flex items-center gap-1">
            <i data-lucide="building-2" class="w-3 h-3 text-slate-400"></i>
            העברה בנקאית:
          </span>
          <span class="font-bold text-slate-800">${formatNIS(item.bank_transfer)}</span>
        </div>
      </div>
    </div>
  `).join('');

  try { lucide.createIcons(); } catch (e) {}
}

function renderFutureCancellationsTable(list) {
  const tbody = document.getElementById('mem-tbody-cancels');
  const countSpan = document.getElementById('mem-table-cancels-count');
  if (!tbody) return;

  const filtered = list.filter(item => {
    if (currentClub === 'gym' && item.branch_key !== 'gym') return false;
    if (currentClub === 'pilates' && item.branch_key !== 'pilates') return false;
    return true;
  });

  if (countSpan) countSpan.innerText = filtered.length;

  if (filtered.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="8" class="text-center py-6 text-slate-400">לא נמצאו מנויים עם ביטול עתידי התואמים את הסינון</td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = filtered.map(item => {
    const refundStatusBadge = item.refund_status
      ? `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold ${item.refund_status.includes('אושר') ? 'bg-amber-100 text-amber-800' : 'bg-emerald-100 text-emerald-800'}">${item.refund_status}</span>`
      : `<span class="text-slate-400 text-[11px]">-</span>`;

    const refundAmountText = item.refund_amount
      ? `<strong class="text-rose-600 font-bold">${formatNIS(item.refund_amount)}</strong>`
      : `<span class="text-slate-400 text-[11px]">-</span>`;

    return `
      <tr class="hover:bg-slate-50 transition border-b border-slate-100 mem-row-cancel" data-search="${(item.name + ' ' + item.branch + ' ' + item.membership_type).toLowerCase()}">
        <td class="py-2.5 px-3 font-bold text-slate-900">${item.name}</td>
        <td class="py-2.5 px-3">
          <span class="px-2 py-0.5 rounded-md text-[10px] font-bold ${item.branch_key === 'pilates' ? 'bg-purple-100 text-purple-800' : 'bg-slate-100 text-slate-800'}">
            ${item.branch}
          </span>
        </td>
        <td class="py-2.5 px-3 text-slate-600">${item.membership_type}</td>
        <td class="py-2.5 px-3 text-center font-semibold text-rose-600">${item.end_date}</td>
        <td class="py-2.5 px-3 text-left font-medium text-slate-700">${formatNIS(item.price)}</td>
        <td class="py-2.5 px-3 text-left font-bold text-blue-600">${formatNIS(item.monthly_price)} / חודש</td>
        <td class="py-2.5 px-3 text-center">${refundStatusBadge}</td>
        <td class="py-2.5 px-3 text-left">${refundAmountText}</td>
      </tr>
    `;
  }).join('');
}

function renderSalesRefundsTable(list) {
  const tbody = document.getElementById('mem-tbody-refunds');
  const countSpan = document.getElementById('mem-table-refunds-count');
  if (!tbody) return;

  if (countSpan) countSpan.innerText = list.length;

  if (list.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="7" class="text-center py-6 text-slate-400">אין בקשות זיכוי רשומות בקובץ המכירות</td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = list.map(item => {
    let statusClass = 'bg-slate-100 text-slate-700';
    if (item.status.includes('אושר') || item.status.includes('ממתין')) {
      statusClass = 'bg-amber-100 text-amber-800';
    } else if (item.status.includes('טופל')) {
      statusClass = 'bg-emerald-100 text-emerald-800';
    } else if (item.status.includes('לא אושר')) {
      statusClass = 'bg-rose-100 text-rose-800';
    }

    return `
      <tr class="hover:bg-slate-50 transition border-b border-slate-100 mem-row-refund" data-search="${(item.name + ' ' + item.type + ' ' + item.status + ' ' + item.notes).toLowerCase()}">
        <td class="py-2.5 px-3 font-bold text-slate-900">${item.name}</td>
        <td class="py-2.5 px-3 text-slate-600">${item.type}</td>
        <td class="py-2.5 px-3 text-slate-500">${item.req_date || '-'}</td>
        <td class="py-2.5 px-3">
          <span class="px-2 py-0.5 rounded-md text-[10px] font-bold ${statusClass}">
            ${item.status}
          </span>
        </td>
        <td class="py-2.5 px-3 text-left font-bold text-slate-900">${formatNIS(item.refund_amount)}</td>
        <td class="py-2.5 px-3 text-slate-500">${item.opener || '-'}</td>
        <td class="py-2.5 px-3 text-slate-500 text-[11px] max-w-xs truncate" title="${item.notes}">${item.notes || '-'}</td>
      </tr>
    `;
  }).join('');
}

function filterMembershipsTables() {
  const query = (document.getElementById('mem-search-input')?.value || '').toLowerCase().trim();

  document.querySelectorAll('.mem-row-cancel').forEach(row => {
    const text = row.getAttribute('data-search') || '';
    row.style.display = text.includes(query) ? '' : 'none';
  });

  document.querySelectorAll('.mem-row-refund').forEach(row => {
    const text = row.getAttribute('data-search') || '';
    row.style.display = text.includes(query) ? '' : 'none';
  });
}

// ============================================================================
// SCHEDULE & TRAINER ATTENDANCE ANALYTICS (מערכת שעות ותפוסה)
// ============================================================================
let scheduleClub = 'מועדון A+';
let scheduleRange = '1m';
let scheduleMode = 'grid'; // 'grid' | 'trainers'
let scheduleAnalyticsData = null;

function setScheduleClub(club) {
  scheduleClub = club;
  document.querySelectorAll('.sched-club-btn').forEach(btn => {
    btn.classList.remove('bg-zinc-900', 'text-white', 'shadow-2xs', 'font-bold');
    btn.classList.add('text-zinc-600', 'hover:bg-zinc-200', 'font-medium');
  });
  const activeId = (club === 'מועדון A+' || club === 'חדר כושר') ? 'sched-club-gym' : 'sched-club-pilates';
  const activeBtn = document.getElementById(activeId);
  if (activeBtn) {
    activeBtn.classList.remove('text-zinc-600', 'hover:bg-zinc-200', 'font-medium');
    activeBtn.classList.add('bg-zinc-900', 'text-white', 'shadow-2xs', 'font-bold');
  }
  const badge = document.getElementById('sched-grid-branch-badge');
  if (badge) badge.innerText = club;
  loadScheduleAnalytics();
}

function setScheduleRange(range) {
  scheduleRange = range;
  document.querySelectorAll('.sched-range-btn').forEach(btn => {
    btn.classList.remove('bg-rose-600', 'text-white', 'shadow-2xs');
    btn.classList.add('text-zinc-600', 'hover:bg-white');
  });
  const activeBtn = document.getElementById(`sched-range-${range}`);
  if (activeBtn) {
    activeBtn.classList.remove('text-zinc-600', 'hover:bg-white');
    activeBtn.classList.add('bg-rose-600', 'text-white', 'shadow-2xs');
  }
  loadScheduleAnalytics();
}

function setScheduleMode(mode) {
  scheduleMode = mode;
  document.querySelectorAll('.sched-mode-btn').forEach(btn => {
    btn.classList.remove('bg-zinc-900', 'text-white', 'shadow-2xs');
    btn.classList.add('text-zinc-600', 'hover:bg-white');
  });
  const activeBtn = document.getElementById(`sched-mode-${mode}`);
  if (activeBtn) {
    activeBtn.classList.remove('text-zinc-600', 'hover:bg-white');
    activeBtn.classList.add('bg-zinc-900', 'text-white', 'shadow-2xs');
  }

  const gridSec = document.getElementById('sched-section-grid');
  const trainersSec = document.getElementById('sched-section-trainers');
  if (gridSec && trainersSec) {
    gridSec.classList.toggle('hidden', mode !== 'grid');
    trainersSec.classList.toggle('hidden', mode !== 'trainers');
  }
}

async function loadScheduleAnalytics() {
  try {
    const url = `/api/schedule_analytics?club=${encodeURIComponent(scheduleClub)}&range=${scheduleRange}&month=${currentMonth}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP error ${res.status}`);
    const data = await res.json();
    scheduleAnalyticsData = data;
    renderScheduleAnalytics(data);
  } catch (err) {
    console.error('Error loading schedule analytics:', err);
    showToast('שגיאה בטעינת נתוני מערכת שעות');
  }
}

function renderScheduleAnalytics(data) {
  if (!data) return;
  const kpis = data.kpis || {};
  const meta = data.metadata || {};
  
  // Update Filter Notice Banner
  const noticeText = document.getElementById('sched-filter-notice-text');
  if (noticeText) {
    const minOcc = meta.min_occurrences || (scheduleRange === '2w' ? 2 : 3);
    const dateRangeStr = (meta.date_from && meta.date_to) ? ` (תקופה: ${meta.date_from} עד ${meta.date_to})` : '';
    noticeText.innerHTML = `מוצגים שיעורים קבועים עם <strong>${minOcc} מופעים ומעלה</strong>${dateRangeStr}. אירועים חד-פעמיים סוננו.`;
  }

  // Update KPI Cards
  const avgOccEl = document.getElementById('sched-kpi-avg-occ');
  if (avgOccEl) avgOccEl.innerText = (kpis.avg_occupancy || 0) + '%';

  const totSessEl = document.getElementById('sched-kpi-total-sessions');
  if (totSessEl) totSessEl.innerText = `${kpis.total_sessions || 0} שיעורים נותחו`;

  const weakCountEl = document.getElementById('sched-kpi-weak-count');
  if (weakCountEl) weakCountEl.innerText = `${kpis.weak_slots_count || 0} משבצות`;

  const peakHourEl = document.getElementById('sched-kpi-peak-hour');
  if (peakHourEl) peakHourEl.innerText = kpis.peak_hour || '--:--';

  const peakDayEl = document.getElementById('sched-kpi-peak-day');
  if (peakDayEl) peakDayEl.innerText = `ביום ${kpis.peak_day || '--'}`;

  const topTrEl = document.getElementById('sched-kpi-top-trainer');
  if (topTrEl) topTrEl.innerText = kpis.top_trainer || '—';

  // Render Timetable Grid
  renderWeeklyTimetable(data.grid || {}, data.days || []);

  // Render Trainers
  renderTrainerAnalytics(data.trainers || []);

  if (window.lucide) lucide.createIcons();
}

function renderWeeklyTimetable(grid, days) {
  const container = document.getElementById('weekly-timetable-days-container');
  if (!container) return;
  container.innerHTML = '';

  days.forEach(dayName => {
    const dayCol = document.createElement('div');
    dayCol.className = 'bg-zinc-50/80 rounded-2xl p-2.5 border border-zinc-200/70 flex flex-col space-y-2';

    // Day Header
    const slotsInDay = grid[dayName] || {};
    const timeKeys = Object.keys(slotsInDay).sort();
    let totalClassesInDay = 0;
    timeKeys.forEach(t => { totalClassesInDay += (slotsInDay[t] || []).length; });

    dayCol.innerHTML = `
      <div class="bg-white px-3 py-2 rounded-xl border border-zinc-200/80 shadow-2xs flex items-center justify-between mb-1">
        <span class="font-black text-xs text-zinc-900">יום ${dayName}</span>
        <span class="text-[10px] font-bold px-1.5 py-0.5 rounded-md bg-zinc-100 text-zinc-600">${totalClassesInDay} שיעורים</span>
      </div>
      <div class="space-y-2 flex-1 custom-scrollbar"></div>
    `;

    const cardsList = dayCol.querySelector('div:last-child');

    if (timeKeys.length === 0) {
      cardsList.innerHTML = `<div class="p-4 text-center text-[10px] text-zinc-400">אין שיעורים קבועים</div>`;
    } else {
      timeKeys.forEach(tKey => {
        const slots = slotsInDay[tKey] || [];
        slots.forEach(s => {
          const tierBorder = s.tier === 'strong' ? 'border-emerald-300 bg-emerald-50/30' :
                             s.tier === 'moderate' ? 'border-amber-300 bg-amber-50/30' :
                             'border-rose-300 bg-rose-50/40';

          const pctBadge = s.tier === 'strong' ? 'bg-emerald-100 text-emerald-800 border-emerald-300' :
                           s.tier === 'moderate' ? 'bg-amber-100 text-amber-800 border-amber-300' :
                           'bg-rose-100 text-rose-800 border-rose-300';

          const subBadge = (s.substitutes && s.substitutes.length > 0) ?
            `<span class="text-[9px] px-1 py-0.2 rounded bg-zinc-100 text-zinc-500 border border-zinc-200" title="החלפות: ${s.substitutes.join(', ')}">הוחלף</span>` : '';

          const card = document.createElement('div');
          card.className = `p-2.5 rounded-xl border ${tierBorder} bg-white shadow-2xs hover:shadow-sm transition flex flex-col space-y-1.5`;
          card.innerHTML = `
            <div class="flex items-center justify-between">
              <span class="text-[11px] font-black text-zinc-900">${s.time}</span>
              <span class="text-[10px] font-black px-1.5 py-0.5 rounded-md border ${pctBadge}">${s.avg_checkin_pct}%</span>
            </div>
            <div>
              <div class="font-black text-xs text-zinc-900 leading-tight">${s.name}</div>
              <div class="text-[11px] text-zinc-500 font-medium flex items-center gap-1 mt-0.5">
                <i data-lucide="user" class="w-3 h-3 text-zinc-400"></i>
                <span class="truncate">${s.primary_trainer}</span>
                ${subBadge}
              </div>
            </div>
            <div class="pt-1.5 border-t border-zinc-100 flex items-center justify-between text-[10px] text-zinc-400 font-medium">
              <span><strong>${s.avg_checkin}</strong> נוכחים</span>
              <span>${s.occurrences} מופעים</span>
            </div>
          `;
          cardsList.appendChild(card);
        });
      });
    }

    container.appendChild(dayCol);
  });
}

function renderTrainerAnalytics(trainers) {
  const container = document.getElementById('trainers-cards-container');
  if (!container) return;
  container.innerHTML = '';

  if (!trainers || trainers.length === 0) {
    container.innerHTML = `<div class="col-span-full p-8 text-center text-xs text-zinc-400">לא נמצאו נתוני מאמנים לתקופה זו</div>`;
    return;
  }

  trainers.forEach(t => {
    const tierBadge = t.tier === 'star' ? 'bg-emerald-100 text-emerald-800 border-emerald-300' :
                      t.tier === 'mid' ? 'bg-amber-100 text-amber-800 border-amber-300' :
                      'bg-rose-100 text-rose-800 border-rose-300';

    const card = document.createElement('div');
    card.className = "bg-white p-4 rounded-2xl border border-zinc-200/80 shadow-2xs hover:shadow-sm transition flex flex-col justify-between space-y-3";
    card.innerHTML = `
      <div class="flex items-start justify-between">
        <div>
          <div class="font-black text-sm text-zinc-900">${t.name}</div>
          <div class="text-[11px] text-zinc-400 font-medium mt-0.5">${t.branches ? t.branches.join(', ') : ''}</div>
        </div>
        <span class="text-[10px] font-black px-2 py-0.5 rounded-lg border ${tierBadge}">${t.avg_checkin_pct}%</span>
      </div>

      <div class="bg-zinc-50 p-2.5 rounded-xl border border-zinc-100 flex items-center justify-between text-xs font-bold text-zinc-700">
        <div class="text-center">
          <div class="text-[10px] text-zinc-400 font-normal">שיעורים</div>
          <div>${t.count}</div>
        </div>
        <div class="text-center border-r border-l border-zinc-200 px-3">
          <div class="text-[10px] text-zinc-400 font-normal">נוכחים ממוצע</div>
          <div class="${t.tier === 'star' ? 'text-emerald-700' : t.tier === 'low' ? 'text-rose-700' : 'text-zinc-800'}">${t.avg_checkin}</div>
        </div>
        <div class="text-center">
          <div class="text-[10px] text-zinc-400 font-normal">ביטולים מאוחרים</div>
          <div class="${t.total_late_cancels > 5 ? 'text-amber-700' : 'text-zinc-700'}">${t.total_late_cancels}</div>
        </div>
      </div>

      <div class="text-[10px] text-zinc-400">
        <span class="font-bold text-zinc-600">שיעורים עיקריים:</span> ${t.classes ? t.classes.join(', ') : '—'}
      </div>
    `;
    container.appendChild(card);
  });
}

// =============================================================================
// MODULE 6: SUPPLIER PAYMENTS & MASAV DASHBOARD (מס״ב ספקים)
// =============================================================================

let suppliersData = null;
let currentSuppliersMonth = 8;
let currentSupplierTermsFilter = 'all';

async function loadSuppliersDashboard(month = null) {
  if (month) currentSuppliersMonth = month;
  try {
    const res = await fetch(`/api/suppliers?month=${currentSuppliersMonth}`);
    suppliersData = await res.json();
    renderSuppliersDashboard(suppliersData);
  } catch (err) {
    console.error('Error loading suppliers dashboard:', err);
    showToast('שגיאה בטעינת נתוני מס״ב ספקים');
  }
}

function renderSuppliersDashboard(data) {
  if (!data) return;
  const kpis = data.financial_kpis || {};
  const byTerms = data.by_terms || {};

  // Top KPIs
  const bankBalEl = document.getElementById('sup-kpi-bank-balance');
  if (bankBalEl) {
    bankBalEl.innerText = formatNIS(kpis.bank_balance);
    bankBalEl.className = kpis.bank_balance >= 0 ? 'text-2xl font-black text-emerald-600' : 'text-2xl font-black text-rose-600';
  }

  const bankSourceEl = document.getElementById('sup-kpi-bank-source');
  if (bankSourceEl) {
    bankSourceEl.innerText = kpis.is_manual_balance ? 'הזנה ידנית (מותאם)' : 'מתוך גיליון תזרים';
  }

  const debtsEl = document.getElementById('sup-kpi-total-debts');
  if (debtsEl) debtsEl.innerText = formatNIS(kpis.total_debts);

  const countEl = document.getElementById('sup-kpi-count');
  if (countEl) countEl.innerText = `${kpis.suppliers_count || 0} שורות`;

  const approvedEl = document.getElementById('sup-kpi-approved-amount');
  if (approvedEl) approvedEl.innerText = formatNIS(kpis.total_approved);

  const approvedCountEl = document.getElementById('sup-kpi-approved-count');
  if (approvedCountEl) approvedCountEl.innerText = `${kpis.approved_count || 0} מאושרים לתשלום`;

  const balanceAfterEl = document.getElementById('sup-kpi-balance-after');
  if (balanceAfterEl) {
    balanceAfterEl.innerText = formatNIS(kpis.balance_after_payment);
    balanceAfterEl.className = kpis.balance_after_payment >= 0 ? 'text-2xl font-black text-emerald-600' : 'text-2xl font-black text-rose-600';
  }

  const balanceTagEl = document.getElementById('sup-kpi-balance-tag');
  if (balanceTagEl) {
    if (kpis.balance_after_payment >= 0) {
      balanceTagEl.innerText = 'יתרה חיובית';
      balanceTagEl.className = 'text-[11px] font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-md';
    } else {
      balanceTagEl.innerText = 'חריגה / גירעון צפוי';
      balanceTagEl.className = 'text-[11px] font-bold text-rose-700 bg-rose-50 px-2 py-0.5 rounded-md';
    }
  }

  const monthLabel = document.getElementById('sup-kpi-month-label');
  if (monthLabel) monthLabel.innerText = `חודש ${data.month_name} 2026`;

  // Filter Buttons Amounts
  const countAllEl = document.getElementById('sup-term-count-all');
  if (countAllEl) countAllEl.innerText = kpis.suppliers_count || 0;

  const amt30El = document.getElementById('sup-term-amount-30');
  if (amt30El) amt30El.innerText = formatNIS(byTerms['+30'] || 0);

  const amt60El = document.getElementById('sup-term-amount-60');
  if (amt60El) amt60El.innerText = formatNIS(byTerms['+60'] || 0);

  const amtImmEl = document.getElementById('sup-term-amount-immediate');
  if (amtImmEl) amtImmEl.innerText = formatNIS(byTerms['immediate'] || 0);

  const amtOverdueEl = document.getElementById('sup-term-amount-overdue');
  if (amtOverdueEl) amtOverdueEl.innerText = formatNIS(byTerms['overdue'] || 0);

  // Render Month Selector
  const monthsContainer = document.getElementById('sup-months-selector');
  if (monthsContainer && data.available_months) {
    const monthNamesMap = { 5: "מאי", 6: "יוני", 7: "יולי", 8: "אוגוסט" };
    monthsContainer.innerHTML = data.available_months.map(m => `
      <button onclick="loadSuppliersDashboard(${m})" class="px-2.5 py-1 rounded-lg transition ${m === currentSuppliersMonth ? 'bg-rose-600 text-white shadow-2xs' : 'text-zinc-600 hover:text-zinc-900'}">
        ${monthNamesMap[m] || m}
      </button>
    `).join('');
  }

  renderSuppliersTable();
  if (window.lucide) lucide.createIcons();
}

function setSupplierTermsFilter(filter) {
  currentSupplierTermsFilter = filter;
  document.querySelectorAll('.sup-term-btn').forEach(btn => {
    btn.className = 'sup-term-btn px-3.5 py-1.5 rounded-xl text-xs font-bold text-zinc-600 hover:bg-zinc-100 transition';
  });

  const activeBtn = document.getElementById(`sup-filter-${filter === '+30' ? '30' : filter === '+60' ? '60' : filter}`);
  if (activeBtn) {
    activeBtn.className = 'sup-term-btn px-3.5 py-1.5 rounded-xl text-xs font-bold bg-zinc-900 text-white transition shadow-2xs';
  }
  renderSuppliersTable();
}

function filterSuppliersTable() {
  renderSuppliersTable();
}

function renderSuppliersTable() {
  if (!suppliersData || !suppliersData.suppliers) return;
  const tbody = document.getElementById('suppliers-table-body');
  if (!tbody) return;

  const searchTerm = (document.getElementById('sup-search-input')?.value || '').trim().toLowerCase();
  
  let filtered = suppliersData.suppliers.filter(s => {
    // Terms filter
    if (currentSupplierTermsFilter === '+30' && s.payment_terms !== '+30') return false;
    if (currentSupplierTermsFilter === '+60' && s.payment_terms !== '+60') return false;
    if (currentSupplierTermsFilter === 'immediate' && !('מזומן' in s.payment_terms || 'מיידי' in s.payment_terms)) return false;
    if (currentSupplierTermsFilter === 'overdue' && !s.is_overdue) return false;

    // Search term
    if (searchTerm) {
      const matchName = s.supplier_name.toLowerCase().includes(searchTerm);
      const matchDesc = s.description.toLowerCase().includes(searchTerm);
      const matchCat = s.category.toLowerCase().includes(searchTerm);
      if (!matchName && !matchDesc && !matchCat) return false;
    }
    return true;
  });

  const countEl = document.getElementById('sup-showing-count');
  if (countEl) countEl.innerText = filtered.length;

  const approvedSum = filtered.filter(s => s.approved).reduce((acc, s) => acc + s.amount, 0);
  const totalApprovedEl = document.getElementById('sup-table-approved-total');
  if (totalApprovedEl) totalApprovedEl.innerText = formatNIS(approvedSum);

  if (filtered.length === 0) {
    tbody.innerHTML = `<tr><td colspan="9" class="text-center py-8 text-zinc-400">לא נמצאו ספקים התואמים את הסינון</td></tr>`;
    return;
  }

  tbody.innerHTML = filtered.map(s => {
    const termsBadge = s.payment_terms === '+30' ? 'bg-blue-50 text-blue-800 border-blue-200' :
                       s.payment_terms === '+60' ? 'bg-purple-50 text-purple-800 border-purple-200' :
                       'bg-zinc-100 text-zinc-800 border-zinc-200';

    const overdueBadge = s.is_overdue ? 
      `<span class="inline-flex items-center gap-1 text-[10px] font-black text-rose-700 bg-rose-50 border border-rose-200 px-2 py-0.5 rounded-md">חריגה: ${s.days_overdue} יום</span>` :
      `<span class="text-[11px] text-zinc-500 font-medium">${s.approx_days} ימים</span>`;

    const contractBadge = s.is_contract ?
      `<span class="inline-flex items-center gap-1 text-[10px] font-black text-amber-800 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded-md">📋 ${s.installment_details || 'הסכם'}</span>` :
      `<span class="text-zinc-300">—</span>`;

    const serviceBadge = (s.service_month !== s.submission_month) ?
      `<div class="flex items-center gap-1">
        <span class="font-bold text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded border border-amber-200 text-[10px]">${s.service_month}</span>
        <span class="text-[10px] text-zinc-400">(הגשה: ${s.submission_month})</span>
      </div>` :
      `<span class="text-xs font-semibold text-zinc-700">${s.service_month}</span>`;

    return `
      <tr class="hover:bg-zinc-50/80 transition-colors ${s.approved ? 'bg-amber-50/20' : ''}">
        <!-- Yellow Approval Checkbox -->
        <td class="py-3 px-4 text-center">
          <input type="checkbox" onchange="toggleSupplierApproval('${s.id}')" ${s.approved ? 'checked' : ''} class="w-4 h-4 rounded text-amber-500 focus:ring-amber-400 border-zinc-300 cursor-pointer accent-amber-400" />
        </td>
        <!-- Supplier Name -->
        <td class="py-3 px-4">
          <div class="font-black text-zinc-900 text-xs">${s.supplier_name}</div>
        </td>
        <!-- Amount -->
        <td class="py-3 px-4 text-left font-black text-zinc-900 text-xs">
          ${formatNIS(s.amount)}
        </td>
        <!-- Payment Terms -->
        <td class="py-3 px-4">
          <span class="text-[10px] font-bold px-2 py-0.5 rounded-md border ${termsBadge}">
            ${s.payment_terms}
          </span>
        </td>
        <!-- Ageing / Overdue -->
        <td class="py-3 px-4">
          ${overdueBadge}
        </td>
        <!-- Service Month vs Submission Month -->
        <td class="py-3 px-4">
          ${serviceBadge}
        </td>
        <!-- Annual Agreement / Installment -->
        <td class="py-3 px-4">
          ${contractBadge}
        </td>
        <!-- Line Description -->
        <td class="py-3 px-4 text-zinc-600 max-w-xs truncate" title="${s.description}">
          ${s.description}
        </td>
        <!-- Category -->
        <td class="py-3 px-4 text-zinc-500 text-[11px]">
          ${s.category}
        </td>
      </tr>
    `;
  }).join('');

  if (window.lucide) lucide.createIcons();
}

async function toggleSupplierApproval(supplierId) {
  if (!suppliersData || !suppliersData.suppliers) return;
  const item = suppliersData.suppliers.find(s => s.id === supplierId);
  if (!item) return;

  item.approved = !item.approved;

  // Compute new approved list
  const approvedIds = suppliersData.suppliers.filter(s => s.approved).map(s => s.id);
  
  // Update local KPIs immediately for snappy UI
  const approvedSum = suppliersData.suppliers.filter(s => s.approved).reduce((acc, s) => acc + s.amount, 0);
  suppliersData.financial_kpis.total_approved = approvedSum;
  suppliersData.financial_kpis.approved_count = approvedIds.length;
  suppliersData.financial_kpis.balance_after_payment = suppliersData.financial_kpis.bank_balance - approvedSum;

  renderSuppliersDashboard(suppliersData);

  // Persist state to backend
  try {
    await fetch('/api/suppliers/state', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        month: currentSuppliersMonth,
        approved_ids: approvedIds
      })
    });
  } catch (err) {
    console.error('Error persisting approval:', err);
  }
}

async function approveAllFilteredSuppliers() {
  if (!suppliersData || !suppliersData.suppliers) return;
  suppliersData.suppliers.forEach(s => s.approved = true);

  const approvedIds = suppliersData.suppliers.map(s => s.id);
  const approvedSum = suppliersData.suppliers.reduce((acc, s) => acc + s.amount, 0);
  suppliersData.financial_kpis.total_approved = approvedSum;
  suppliersData.financial_kpis.approved_count = approvedIds.length;
  suppliersData.financial_kpis.balance_after_payment = suppliersData.financial_kpis.bank_balance - approvedSum;

  renderSuppliersDashboard(suppliersData);

  try {
    await fetch('/api/suppliers/state', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        month: currentSuppliersMonth,
        approved_ids: approvedIds
      })
    });
    showToast('כל הספקים אושרו לתשלום');
  } catch (err) {
    console.error('Error saving approvals:', err);
  }
}

// Bank Balance Modal Handlers
function openBankBalanceModal() {
  const modal = document.getElementById('bank-balance-modal');
  const input = document.getElementById('bank-balance-input');
  if (suppliersData && suppliersData.financial_kpis && input) {
    input.value = suppliersData.financial_kpis.bank_balance || '';
  }
  if (modal) {
    modal.classList.remove('hidden');
    setTimeout(() => {
      modal.classList.remove('opacity-0');
      document.getElementById('bank-balance-modal-card')?.classList.remove('scale-95');
    }, 10);
  }
}

function closeBankBalanceModal() {
  const modal = document.getElementById('bank-balance-modal');
  if (modal) {
    modal.classList.add('opacity-0');
    document.getElementById('bank-balance-modal-card')?.classList.add('scale-95');
    setTimeout(() => modal.classList.add('hidden'), 200);
  }
}

async function saveBankBalance() {
  const input = document.getElementById('bank-balance-input');
  const val = parseFloat(input?.value);
  if (isNaN(val)) {
    showToast('נא להזין מספר תקין');
    return;
  }

  try {
    const res = await fetch('/api/suppliers/state', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        month: currentSuppliersMonth,
        bank_balance: val
      })
    });
    const result = await res.json();
    if (result.success && result.data) {
      suppliersData = result.data;
      renderSuppliersDashboard(suppliersData);
      closeBankBalanceModal();
      showToast('יתרת הבנק עודכנה בהצלחה');
    }
  } catch (err) {
    console.error('Error saving bank balance:', err);
    showToast('שגיאה בשמירת יתרת הבנק');
  }
}

function initDashboard() {
  const now = new Date();
  const calMonth = now.getMonth() + 1;
  if (calMonth >= 1 && calMonth <= 12) {
    currentMonth = calMonth;
  }
  const monthDisplay = document.getElementById('current-month-display');
  if (monthDisplay) {
    monthDisplay.innerText = `${MONTH_NAMES[currentMonth - 1]} ${now.getFullYear()}`;
  }

  const modalEl = document.getElementById('drilldown-modal');
  if (modalEl) {
    modalEl.addEventListener('click', (e) => {
      if (e.target.id === 'drilldown-modal') closeModal();
    });
  }
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closeModal();
      closeBankBalanceModal();
    }
  });
  fetchDashboardData();
}

// =============================================================================
// REVENUE BREAKDOWN — Live Arbox, PT, Studio & Platform Breakdown
// =============================================================================

let cachedRevenueBreakdown = null;

function renderRevenueBreakdown(data) {
  if (!data) return;
  cachedRevenueBreakdown = data;

  const totalDisplay = document.getElementById('rev-breakdown-total-display');
  const netTotalDisplay = document.getElementById('rev-breakdown-net-total-display');
  if (totalDisplay && data.totals) {
    totalDisplay.innerText = formatNIS(data.totals.total_gross || data.totals.estimated);
  }
  if (netTotalDisplay && data.totals) {
    netTotalDisplay.innerText = formatNIS(data.totals.total_net);
  }

  const tbody = document.getElementById('revenue-breakdown-tbody');
  const tfoot = document.getElementById('revenue-breakdown-tfoot');
  if (!tbody || !data.rows) return;

  tbody.innerHTML = data.rows.map((row) => {
    const isOverride = row.override !== null && row.override !== undefined;
    const grossVal = (row.gross !== null && row.gross !== undefined) ? row.gross : 0;
    const netVal = (row.net !== null && row.net !== undefined) ? row.net : 0;

    return `
      <tr class="hover:bg-slate-50/80 transition-colors">
        <td class="py-2.5 px-3.5 font-mono text-slate-600 font-bold whitespace-nowrap">${row.code}</td>
        <td class="py-2.5 px-3 whitespace-nowrap">
          <div class="font-bold text-slate-900">${row.label}</div>
        </td>
        <td class="py-2.5 px-3 text-center whitespace-nowrap">
          <span class="px-2.5 py-0.5 rounded-md text-[10px] font-bold ${row.branch === 'פילאטיס' ? 'bg-purple-50 text-purple-700 border border-purple-200' : 'bg-blue-50 text-blue-700 border border-blue-200'}">
            ${row.branch}
          </span>
        </td>
        <td class="py-2.5 px-3 text-left whitespace-nowrap">
          <span class="font-black text-emerald-800 text-sm">${formatNIS(grossVal)}</span>
        </td>
        <td class="py-2.5 px-3 text-left whitespace-nowrap">
          <span class="font-bold text-slate-700 text-xs">${formatNIS(netVal)}</span>
        </td>
        <td class="py-2.5 px-3 text-left whitespace-nowrap font-medium text-slate-400">
          ${row.actual_ledger > 0 ? formatNIS(row.actual_ledger) : '<span class="text-slate-300">₪ 0 (טרם נסגר)</span>'}
        </td>
        <td class="py-2.5 px-3 text-slate-500 text-[11px] whitespace-nowrap">
          ${row.arbox_metric || '—'}
        </td>
        <td class="py-2.5 px-3 text-center">
          <input 
            type="number" 
            value="${isOverride ? row.override : ''}" 
            placeholder="${Math.round(grossVal)}" 
            onchange="handleRevenueOverride('${row.code}', this.value)"
            class="w-32 text-center px-2.5 py-1 rounded-lg border ${isOverride ? 'border-emerald-500 bg-emerald-50 font-black text-emerald-900' : 'border-slate-200 bg-white font-medium text-slate-700'} text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500 shadow-2xs"
            title="הזן סכום ברוטו (כולל מע״מ) לכיוונון ידני בלייב"
          />
        </td>
      </tr>
    `;
  }).join('');

  if (tfoot && data.totals) {
    tfoot.innerHTML = `
      <tr class="bg-slate-50/90 font-black text-slate-900 border-t-2 border-slate-200">
        <td class="py-3 px-3.5 whitespace-nowrap" colspan="3">סה״כ הכנסות (חודשי)</td>
        <td class="py-3 px-3 text-left text-emerald-900 font-black text-sm whitespace-nowrap">${formatNIS(data.totals.total_gross)}</td>
        <td class="py-3 px-3 text-left text-slate-800 font-black text-xs whitespace-nowrap">${formatNIS(data.totals.total_net)}</td>
        <td class="py-3 px-3 text-left text-slate-500 font-bold text-xs whitespace-nowrap">${data.totals.actual_ledger > 0 ? formatNIS(data.totals.actual_ledger) : '₪ 0'}</td>
        <td class="py-3 px-3" colspan="2"></td>
      </tr>
    `;
  }
}

async function handleRevenueOverride(code, val) {
  const num = val === '' ? null : parseFloat(val);
  const monthKey = `2026-${String(currentMonth).padStart(2, '0')}`;
  
  try {
    const res = await fetch('/api/revenue_breakdown/override', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ month_key: monthKey, code: code, value: num })
    });
    const data = await res.json();
    if (data.success) {
      showToast('הכיוונון נשמר בהצלחה');
      fetchDashboardData();
    }
  } catch (err) {
    showToast('שגיאה בשמירת הכיוונון');
  }
}

// =============================================================================
// TASKS BOARD — Club Operations Management
// =============================================================================

let tasksData = null;
let currentTaskFilter = 'all';

async function loadTasksBoard() {
  try {
    const res = await fetch('/api/tasks');
    tasksData = await res.json();
    renderTasksBoard(tasksData);
  } catch (err) {
    console.error('Error loading tasks:', err);
    showToast('שגיאה בטעינת לוח המשימות');
  }
}

function renderTasksBoard(data) {
  if (!data) return;
  const summ = data.summary || {};

  const kpiTotal = document.getElementById('task-kpi-total');
  const kpiOverdue = document.getElementById('task-kpi-overdue');
  const kpiDueToday = document.getElementById('task-kpi-due-today');
  const kpiCompleted = document.getElementById('task-kpi-completed-week');
  const navBadge = document.getElementById('tasks-nav-badge');
  const lastUpdated = document.getElementById('tasks-last-updated');

  if (kpiTotal) kpiTotal.innerText = summ.total || 0;
  if (kpiOverdue) kpiOverdue.innerText = summ.overdue || 0;
  if (kpiDueToday) kpiDueToday.innerText = summ.due_today || 0;
  if (kpiCompleted) kpiCompleted.innerText = summ.completed_this_week || 0;

  if (navBadge) {
    const urgentCount = (summ.overdue || 0) + (summ.due_today || 0);
    if (urgentCount > 0) {
      navBadge.innerText = urgentCount;
      navBadge.classList.remove('hidden');
    } else {
      navBadge.classList.add('hidden');
    }
  }

  if (lastUpdated) {
    lastUpdated.innerText = new Date().toLocaleTimeString('he-IL', { hour: '2-digit', minute: '2-digit' });
  }

  renderTasksList();
}

function filterTasks(filterType) {
  currentTaskFilter = filterType;
  document.querySelectorAll('.task-filter-btn').forEach(btn => {
    btn.className = 'task-filter-btn px-3 py-1 rounded-xl text-xs font-bold text-zinc-600 hover:bg-zinc-100';
  });
  const activeBtn = document.getElementById(`task-filter-${filterType}`);
  if (activeBtn) {
    if (filterType === 'urgent') {
      activeBtn.className = 'task-filter-btn px-3 py-1 rounded-xl text-xs font-black bg-rose-600 text-white shadow-2xs';
    } else {
      activeBtn.className = 'task-filter-btn px-3 py-1 rounded-xl text-xs font-black bg-zinc-900 text-white shadow-2xs';
    }
  }
  renderTasksList();
}

function renderTasksList() {
  if (!tasksData || !tasksData.tasks) return;
  const container = document.getElementById('tasks-list-container');
  if (!container) return;

  let list = tasksData.tasks;
  if (currentTaskFilter === 'daily') list = list.filter(t => t.recurrence === 'daily');
  else if (currentTaskFilter === 'weekly') list = list.filter(t => t.recurrence === 'weekly');
  else if (currentTaskFilter === 'monthly') list = list.filter(t => t.recurrence === 'monthly');
  else if (currentTaskFilter === 'urgent') list = list.filter(t => t.urgency === 'overdue' || t.urgency === 'due_today' || t.priority === 'high');

  if (list.length === 0) {
    container.innerHTML = `
      <div class="bg-white rounded-3xl p-8 border border-zinc-200 text-center text-zinc-400 space-y-2">
        <i data-lucide="check-circle" class="w-8 h-8 text-emerald-500 mx-auto"></i>
        <div class="font-bold text-zinc-700">אין משימות להצגה בסינון זה</div>
        <div class="text-xs">כל המשימות בוצעו או שאין שגרות פעילות</div>
      </div>
    `;
    if (window.lucide) lucide.createIcons();
    return;
  }

  container.innerHTML = list.map(t => {
    // Urgency styling
    let urgencyBadge = '';
    let cardBorder = 'border-zinc-200/80';
    let cardBg = 'bg-white';

    if (t.urgency === 'overdue') {
      urgencyBadge = `<span class="px-2 py-0.5 rounded-md text-[10px] font-black bg-rose-100 text-rose-800 border border-rose-200">⚠️ באיחור של ${Math.abs(t.days_until_due || 1)} ימים</span>`;
      cardBorder = 'border-rose-300';
      cardBg = 'bg-rose-50/30';
    } else if (t.urgency === 'due_today') {
      urgencyBadge = `<span class="px-2 py-0.5 rounded-md text-[10px] font-black bg-amber-100 text-amber-800 border border-amber-200">🔥 לביצוע היום</span>`;
      cardBorder = 'border-amber-300';
      cardBg = 'bg-amber-50/20';
    } else if (t.urgency === 'soon') {
      urgencyBadge = `<span class="px-2 py-0.5 rounded-md text-[10px] font-bold bg-indigo-50 text-indigo-700 border border-indigo-200">מועד קרוב (בעוד ${t.days_until_due} ימים)</span>`;
    }

    // Recurrence label
    const recLabel = t.recurrence === 'daily' ? '🔄 שגרה יומית' :
                     t.recurrence === 'weekly' ? '📅 שגרה שבועית' :
                     t.recurrence === 'monthly' ? '🗓️ שגרה חודשית' : '📌 משימה חד-פעמית';

    return `
      <div class="rounded-2xl border ${cardBorder} ${cardBg} p-4 shadow-2xs hover:shadow-xs transition space-y-2.5">
        <div class="flex items-start justify-between gap-3">
          <div class="flex items-start gap-3">
            <button onclick="markTaskDone('${t.id}')" class="mt-0.5 w-6 h-6 rounded-lg border-2 border-zinc-300 hover:border-emerald-500 hover:bg-emerald-50 text-emerald-600 flex items-center justify-center transition shrink-0" title="סמן כבוצע (יאופס אוטומטית למחזור הבא)">
              <i data-lucide="check" class="w-3.5 h-3.5"></i>
            </button>
            <div>
              <div class="flex items-center gap-2 flex-wrap">
                <h4 class="font-black text-sm text-zinc-900">${t.title}</h4>
                <span class="text-[10px] font-bold px-2 py-0.5 bg-zinc-100 text-zinc-700 rounded-md">${recLabel}</span>
                ${urgencyBadge}
              </div>
              <p class="text-xs text-zinc-600 mt-1 leading-relaxed">${t.description}</p>
            </div>
          </div>
          <div class="text-left shrink-0 text-xs">
            ${t.computed_next_due ? `<span class="font-mono text-zinc-500 block text-[11px]">יעד: <strong>${t.computed_next_due}</strong></span>` : ''}
            ${t.last_completed ? `<span class="text-[10px] text-emerald-600 font-semibold block">בוצע לאחרונה: ${t.last_completed.split('T')[0]}</span>` : ''}
          </div>
        </div>

        ${(t.checklist && t.checklist.length > 0) ? `
          <div class="pt-2 border-t border-zinc-100 text-xs">
            <div class="font-bold text-zinc-500 text-[10px] mb-1">פירוט שלבי ביצוע (Checklist):</div>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-1">
              ${t.checklist.map((item, idx) => `
                <label class="flex items-center gap-1.5 text-zinc-700 cursor-pointer text-[11px]">
                  <input type="checkbox" class="w-3.5 h-3.5 rounded text-rose-600 border-zinc-300 accent-rose-600" />
                  <span>${item}</span>
                </label>
              `).join('')}
            </div>
          </div>
        ` : ''}
      </div>
    `;
  }).join('');

  if (window.lucide) lucide.createIcons();
}

async function markTaskDone(taskId) {
  try {
    const res = await fetch('/api/tasks/complete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task_id: taskId })
    });
    const data = await res.json();
    if (data.success) {
      showToast('המשימה הושלמה בהצלחה! השגרה אופסה למחזור הבא ✅');
      loadTasksBoard();
    }
  } catch (err) {
    showToast('שגיאה בעדכון המשימה');
  }
}

function openNewTaskModal() {
  const modal = document.getElementById('task-modal');
  const card = document.getElementById('task-modal-card');
  if (!modal || !card) return;
  modal.classList.remove('hidden');
  setTimeout(() => {
    modal.classList.remove('opacity-0');
    card.classList.remove('scale-95');
    card.classList.add('scale-100');
  }, 10);
  if (window.lucide) lucide.createIcons();
}

function closeTaskModal() {
  const modal = document.getElementById('task-modal');
  const card = document.getElementById('task-modal-card');
  if (!modal || !card) return;
  modal.classList.add('opacity-0');
  card.classList.remove('scale-100');
  card.classList.add('scale-95');
  setTimeout(() => { modal.classList.add('hidden'); }, 200);
}

async function saveTaskFromModal() {
  const title = document.getElementById('task-input-title')?.value.trim();
  const desc = document.getElementById('task-input-desc')?.value.trim();
  const recurrence = document.getElementById('task-input-recurrence')?.value;
  const priority = document.getElementById('task-input-priority')?.value;
  const dueDate = document.getElementById('task-input-due')?.value || null;
  const followupDate = document.getElementById('task-input-followup')?.value || null;

  if (!title) {
    showToast('נא להזין שם למשימה');
    return;
  }

  const payload = {
    title,
    description: desc,
    recurrence,
    priority,
    due_date: dueDate,
    followup_date: followupDate,
    checklist: [],
    is_custom: true
  };

  try {
    const res = await fetch('/api/tasks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data.success) {
      showToast('המשימה נשמרה בהצלחה!');
      closeTaskModal();
      loadTasksBoard();
    }
  } catch (err) {
    showToast('שגיאה בשמירת המשימה');
  }
}

// =============================================================================
// MASAV TRANSMISSION & BOOKKEEPER WORKFLOW
// =============================================================================

async function transmitMasav() {
  if (!suppliersData || !suppliersData.suppliers) return;
  const approvedCount = suppliersData.suppliers.filter(s => s.approved).length;
  if (approvedCount === 0) {
    showToast('אין ספקים מסומנים לאישור תשלום');
    return;
  }

  const confirmed = confirm(`האם לאשר שידור מס״ב עבור ${approvedCount} ספקים מאושרים ולהעבירם לארכיון?`);
  if (!confirmed) return;

  try {
    const res = await fetch('/api/suppliers/transmit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ month: currentMonth })
    });
    const result = await res.json();
    if (result.success) {
      showToast(`המסמך יצא! ${result.result.archived_count} ספקים הועברו לארכיון מס״ב ✅`);
      loadSuppliersDashboard();
    }
  } catch (err) {
    showToast('שגיאה בביצוע שידור מס״ב');
  }
}

function openBookkeeperModal() {
  const modal = document.getElementById('bookkeeper-modal');
  const card = document.getElementById('bookkeeper-modal-card');
  if (!modal || !card) return;
  modal.classList.remove('hidden');
  setTimeout(() => {
    modal.classList.remove('opacity-0');
    card.classList.remove('scale-95');
    card.classList.add('scale-100');
  }, 10);
  if (window.lucide) lucide.createIcons();
}

function closeBookkeeperModal() {
  const modal = document.getElementById('bookkeeper-modal');
  const card = document.getElementById('bookkeeper-modal-card');
  if (!modal || !card) return;
  modal.classList.add('opacity-0');
  card.classList.remove('scale-100');
  card.classList.add('scale-95');
  setTimeout(() => { modal.classList.add('hidden'); }, 200);
}

function handleInvoiceFileUpload(event) {
  const file = event.target.files[0];
  if (!file) return;

  const statusEl = document.getElementById('upload-status-display');
  if (statusEl) {
    statusEl.classList.remove('hidden');
    statusEl.innerText = `מעלה את ${file.name}...`;
  }

  const reader = new FileReader();
  reader.onload = async function() {
    const base64Data = reader.result.split(',')[1];
    try {
      const res = await fetch('/api/upload_invoice', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          filename: file.name,
          content_base64: base64Data
        })
      });
      const data = await res.json();
      if (data.success) {
        if (statusEl) {
          statusEl.innerText = `✅ הקובץ ${file.name} נשמר בהצלחה בתיקיית הספקים!`;
        }
        showToast(`החשבונית ${file.name} נשמרה בהצלחה!`);
      }
    } catch (err) {
      if (statusEl) statusEl.innerText = '❌ שגיאה בהעלאת הקובץ';
    }
  };
  reader.readAsDataURL(file);
}

// Global exposure
window.handleRevenueOverride = handleRevenueOverride;
window.filterTasks = filterTasks;
window.markTaskDone = markTaskDone;
window.openNewTaskModal = openNewTaskModal;
window.closeTaskModal = closeTaskModal;
window.saveTaskFromModal = saveTaskFromModal;
window.transmitMasav = transmitMasav;
window.openBookkeeperModal = openBookkeeperModal;
window.closeBookkeeperModal = closeBookkeeperModal;
window.handleInvoiceFileUpload = handleInvoiceFileUpload;

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initDashboard);
} else {
  initDashboard();
}

