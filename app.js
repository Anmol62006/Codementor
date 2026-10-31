/**
 * CodeMentor — Application Frontend Logic
 * Interactive 8-Stage Stepper, Code Editor with Line Numbers,
 * Persistent Debugging DNA Dashboard, and Sandboxed Test Runner.
 */

const STATE = {
  userId: 1,
  language: 'en', // 'en' or 'hinglish'
  theme: 'dark',
  currentView: 'dashboard',
  currentAttemptId: null,
  currentProblem: null,
  currentStageData: null,
  originalBuggyCode: '',
  problemsCatalog: [],
  users: []
};

// ==================== INITIALIZATION ====================
document.addEventListener('DOMContentLoaded', async () => {
  initTheme();
  setupEventListeners();
  await loadSystemHealth();
  await loadUsers();
  await loadProblems();
  await loadStudentDNA();
});

function initTheme() {
  const savedTheme = localStorage.getItem('codementor_theme') || 'dark';
  setTheme(savedTheme);
}

function setTheme(theme) {
  STATE.theme = theme;
  document.body.className = theme === 'light' ? 'light-theme' : 'dark-theme';
  localStorage.setItem('codementor_theme', theme);
}

// ==================== EVENT LISTENERS ====================
function setupEventListeners() {
  // Navigation tabs
  document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const view = btn.dataset.view;
      switchView(view);
    });
  });

  // Language switcher (English / Hinglish)
  document.querySelectorAll('.lang-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      document.querySelectorAll('.lang-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      STATE.language = btn.dataset.lang;
      updateLanguageIndicator();
      if (STATE.currentAttemptId && STATE.currentView === 'workspace') {
        await reloadCurrentStage();
      }
    });
  });

  // Student Switcher
  const userSelect = document.getElementById('user-select');
  userSelect.addEventListener('change', async (e) => {
    const val = e.target.value;
    if (val === 'new') {
      showRegisterModal();
    } else {
      STATE.userId = parseInt(val, 10);
      await loadStudentDNA();
    }
  });

  // Theme Toggle
  document.getElementById('theme-toggle').addEventListener('click', () => {
    setTheme(STATE.theme === 'dark' ? 'light' : 'dark');
  });

  // Quick Practice Button on Dashboard
  document.getElementById('btn-quick-practice').addEventListener('click', () => {
    switchView('catalog');
  });

  // Empty state start button
  document.getElementById('btn-empty-start').addEventListener('click', () => {
    switchView('catalog');
  });

  // Catalog Filter
  document.getElementById('filter-language').addEventListener('change', (e) => {
    filterProblems(e.target.value);
  });

  // Back button in workspace
  document.getElementById('btn-back-to-catalog').addEventListener('click', () => {
    switchView('catalog');
  });

  // Code Editor Line Numbers & Tab key
  const editor = document.getElementById('code-editor');
  editor.addEventListener('input', updateLineNumbers);
  editor.addEventListener('scroll', syncEditorScroll);
  editor.addEventListener('keydown', handleEditorKeyDown);

  // Editor Actions
  document.getElementById('btn-reset-code').addEventListener('click', resetEditorCode);
  document.getElementById('btn-verify-code').addEventListener('click', runAndVerifyCode);
  document.getElementById('btn-unlock-solution').addEventListener('click', unlockFullSolution);

  // Stepper Items Direct Click
  document.querySelectorAll('.step-item').forEach(item => {
    item.addEventListener('click', async () => {
      if (!STATE.currentAttemptId) return;
      const stage = parseInt(item.dataset.stage, 10);
      await jumpToStage(stage);
    });
  });

  // Custom Debug Form Submit
  document.getElementById('form-custom-debug').addEventListener('submit', handleCustomDebugSubmit);

  // Register Modal Close & Submit
  document.getElementById('modal-close-btn').addEventListener('click', hideRegisterModal);
  document.getElementById('modal-cancel-btn').addEventListener('click', hideRegisterModal);
  document.getElementById('form-register').addEventListener('submit', handleRegisterSubmit);
}

// ==================== VIEW SWITCHING ====================
function switchView(viewName) {
  STATE.currentView = viewName;
  document.querySelectorAll('.app-view').forEach(v => v.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));

  const viewEl = document.getElementById(`view-${viewName}`);
  if (viewEl) viewEl.classList.add('active');

  const navBtn = document.querySelector(`.nav-btn[data-view="${viewName}"]`);
  if (navBtn) navBtn.classList.add('active');

  if (viewName === 'dashboard') {
    loadStudentDNA();
  }
}

function updateLanguageIndicator() {
  const ind = document.getElementById('ws-lang-indicator');
  if (ind) {
    ind.textContent = STATE.language === 'hinglish' ? 'हिन्दी / Hinglish' : 'English';
  }
}

// ==================== SYSTEM & USERS DATA ====================
async function loadSystemHealth() {
  try {
    const res = await fetch('/api/health');
    const data = await res.json();
    const pill = document.getElementById('system-status-text');
    if (data.compilers && data.compilers.gcc_c) {
      pill.textContent = 'GCC & Python Sandbox Ready';
    } else {
      pill.textContent = 'Python Sandbox Ready';
    }
  } catch (err) {
    console.error('Failed to load system health:', err);
  }
}

async function loadUsers() {
  try {
    const res = await fetch('/api/users');
    const data = await res.json();
    STATE.users = data.users || [];
    renderUserSelector();
  } catch (err) {
    console.error('Failed to load users:', err);
  }
}

function renderUserSelector() {
  const sel = document.getElementById('user-select');
  sel.innerHTML = '';
  STATE.users.forEach(u => {
    const opt = document.createElement('option');
    opt.value = u.id;
    opt.textContent = `${u.display_name} (${u.username})`;
    if (u.id === STATE.userId) opt.selected = true;
    sel.appendChild(opt);
  });

  const newOpt = document.createElement('option');
  newOpt.value = 'new';
  newOpt.textContent = '+ Register New Student...';
  sel.appendChild(newOpt);
}

// ==================== FEATURE 1: DEBUGGING DNA DASHBOARD ====================
async function loadStudentDNA() {
  try {
    const res = await fetch(`/api/dna/${STATE.userId}`);
    const dna = await res.json();
    renderStudentDNA(dna);
  } catch (err) {
    console.error('Failed to load student DNA:', err);
  }
}

function renderStudentDNA(dna) {
  const user = dna.user || {};
  const summary = dna.summary || {};

  // Profile Header
  document.getElementById('student-name').textContent = user.display_name || 'Student';
  const initials = (user.display_name || 'ST')
    .split(' ')
    .map(p => p[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
  document.getElementById('student-avatar').textContent = initials;

  // Handle Empty State
  const emptyCard = document.getElementById('dashboard-empty-state');
  const metricsGrid = document.querySelector('.metrics-grid');
  const panelsGrid = document.querySelector('.dna-panels-grid');
  const insightsGrid = document.querySelector('.dna-insights-grid');

  if (dna.empty_state) {
    emptyCard.style.display = 'block';
    metricsGrid.style.display = 'none';
    panelsGrid.style.display = 'none';
    insightsGrid.style.display = 'none';

    // Render Welcome Insight
    renderInsights(dna.personalized_insights || []);
    return;
  }

  emptyCard.style.display = 'none';
  metricsGrid.style.display = 'grid';
  panelsGrid.style.display = 'grid';
  insightsGrid.style.display = 'grid';

  // Metrics Cards (Real DB numbers, strictly derived)
  document.getElementById('val-total-attempts').textContent = summary.total_attempts || 0;
  document.getElementById('val-solve-rate').textContent = `${summary.solve_rate || 0}%`;
  document.getElementById('val-solved-ratio').textContent = `${summary.solved_count || 0} of ${summary.total_attempts || 0} solved`;
  document.getElementById('val-avg-hints').textContent = summary.avg_hints_per_solved || '0.0';

  const topMistake = dna.mistake_distribution && dna.mistake_distribution.length > 0
    ? dna.mistake_distribution[0]
    : null;
  document.getElementById('val-top-mistake').textContent = topMistake ? topMistake.name : 'None';
  document.getElementById('val-top-mistake-sub').textContent = topMistake
    ? `${topMistake.count} recorded attempt(s)`
    : 'No errors logged';

  // Render Personalized Insights
  renderInsights(dna.personalized_insights || []);

  // Render Mistake Distribution Bars
  renderMistakeBars(dna.mistake_distribution || []);

  // Render Activity Timeline Chart
  renderTimelineChart(dna.timeline || []);

  // Render Needing Practice & Improving Lists
  renderConceptLists(dna.concepts_needing_practice || [], dna.concepts_improving || []);
}

function renderInsights(insights) {
  const container = document.getElementById('insights-container');
  container.innerHTML = '';

  insights.forEach(ins => {
    const card = document.createElement('div');
    card.className = `insight-card ${ins.type}`;

    let iconSvg = '';
    if (ins.type === 'top_mistake' || ins.type === 'practice_needed') {
      iconSvg = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`;
    } else if (ins.type === 'improvement') {
      iconSvg = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>`;
    } else {
      iconSvg = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#6366f1" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>`;
    }

    card.innerHTML = `
      <div class="insight-icon">${iconSvg}</div>
      <div class="insight-content">
        <h4>${ins.title || 'Learning Insight'}</h4>
        <p>${escapeHtml(ins.text)}</p>
      </div>
    `;
    container.appendChild(card);
  });
}

function renderMistakeBars(categories) {
  const container = document.getElementById('category-bars-container');
  container.innerHTML = '';

  if (categories.length === 0) {
    container.innerHTML = '<p class="text-muted text-sm">No mistakes recorded yet.</p>';
    return;
  }

  categories.forEach(cat => {
    const item = document.createElement('div');
    item.className = 'cat-bar-item';
    item.innerHTML = `
      <div class="cat-bar-header">
        <span class="flex-center gap-2">
          <strong style="color: ${cat.color || '#6366f1'}">${escapeHtml(cat.name)}</strong>
          <span class="text-muted text-sm">(${cat.count} attempts &bull; ${cat.solved} solved)</span>
        </span>
        <span class="font-mono text-sm">${cat.percentage}%</span>
      </div>
      <div class="cat-bar-track">
        <div class="cat-bar-fill" style="width: ${cat.percentage}%; background-color: ${cat.color || '#6366f1'}"></div>
      </div>
    `;
    container.appendChild(item);
  });
}

function renderTimelineChart(timeline) {
  const container = document.getElementById('timeline-chart-box');
  container.innerHTML = '';

  if (timeline.length === 0) {
    container.innerHTML = '<p class="text-muted text-sm">No timeline activity to display.</p>';
    return;
  }

  const maxVal = Math.max(...timeline.map(t => t.attempts), 1);
  const chartHeight = 140;
  const colWidth = Math.max(48, Math.floor(320 / timeline.length));

  let barsHtml = '';
  timeline.forEach((item, idx) => {
    const barHeight = Math.max(12, Math.round((item.attempts / maxVal) * (chartHeight - 40)));
    const solvedHeight = Math.round((item.solved / maxVal) * (chartHeight - 40));
    const x = idx * (colWidth + 12) + 20;
    const y = chartHeight - 24 - barHeight;

    barsHtml += `
      <g class="chart-col" transform="translate(${x}, 0)">
        <!-- Total Attempts Bar -->
        <rect x="0" y="${y}" width="${colWidth}" height="${barHeight}" rx="4" fill="#6366f1" opacity="0.3"></rect>
        <!-- Solved Bar -->
        <rect x="0" y="${chartHeight - 24 - solvedHeight}" width="${colWidth}" height="${solvedHeight}" rx="4" fill="#10b981"></rect>
        <!-- Label Count -->
        <text x="${colWidth / 2}" y="${y - 6}" text-anchor="middle" fill="#9ca3af" font-size="11" font-family="Inter">${item.attempts}</text>
        <!-- Date Label -->
        <text x="${colWidth / 2}" y="${chartHeight - 6}" text-anchor="middle" fill="#6b7280" font-size="10" font-family="Inter">${item.date.slice(5)}</text>
      </g>
    `;
  });

  const svgWidth = Math.max(340, timeline.length * (colWidth + 12) + 40);
  container.innerHTML = `
    <svg width="100%" height="${chartHeight}" viewBox="0 0 ${svgWidth} ${chartHeight}" style="overflow: visible;">
      ${barsHtml}
    </svg>
  `;
}

function renderConceptLists(needingPractice, improving) {
  const needEl = document.getElementById('concepts-needing-practice');
  const impEl = document.getElementById('concepts-improving');

  needEl.innerHTML = needingPractice.length === 0
    ? '<p class="text-muted text-sm">Great job! No weak concepts identified yet.</p>'
    : needingPractice.map(c => `
      <div class="concept-item">
        <h5>${escapeHtml(c.name)}</h5>
        <p>${escapeHtml(c.reason)}</p>
      </div>
    `).join('');

  impEl.innerHTML = improving.length === 0
    ? '<p class="text-muted text-sm">Solve more problems to demonstrate mastery.</p>'
    : improving.map(c => `
      <div class="concept-item">
        <h5>${escapeHtml(c.name)}</h5>
        <p>${escapeHtml(c.reason)}</p>
      </div>
    `).join('');
}

// ==================== FEATURE 2: CURATED PROBLEMS CATALOG ====================
async function loadProblems() {
  try {
    const res = await fetch('/api/problems');
    const data = await res.json();
    STATE.problemsCatalog = data.problems || [];
    renderProblemsCatalog(STATE.problemsCatalog);
  } catch (err) {
    console.error('Failed to load problems:', err);
  }
}

function filterProblems(lang) {
  if (lang === 'all') {
    renderProblemsCatalog(STATE.problemsCatalog);
  } else {
    const filtered = STATE.problemsCatalog.filter(p => p.language.toLowerCase() === lang.toLowerCase());
    renderProblemsCatalog(filtered);
  }
}

function renderProblemsCatalog(problems) {
  const grid = document.getElementById('problems-grid');
  grid.innerHTML = '';

  problems.forEach(prob => {
    const card = document.createElement('div');
    card.className = 'problem-card';
    card.innerHTML = `
      <div>
        <div class="flex-center gap-2" style="margin-bottom: 8px;">
          <span class="badge badge-lang">${prob.language.toUpperCase()}</span>
          <span class="badge badge-diff">${prob.difficulty}</span>
        </div>
        <h3 class="problem-title">${escapeHtml(prob.title)}</h3>
        <p class="problem-desc">${escapeHtml(prob.description)}</p>
      </div>
      <div class="problem-footer">
        <span class="badge badge-concept">${escapeHtml(prob.concept)}</span>
        <button class="btn btn-primary btn-sm" onclick="startDebuggingProblem(${prob.id})">
          Debug Challenge &rarr;
        </button>
      </div>
    `;
    grid.appendChild(card);
  });
}

// ==================== FEATURE 3: HINT-FIRST WORKSPACE ====================
async function startDebuggingProblem(problemId) {
  try {
    const res = await fetch('/api/attempts/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: STATE.userId,
        problem_id: problemId,
        lang: STATE.language
      })
    });
    const data = await res.json();
    if (data.error) {
      alert(`Error starting session: ${data.error}`);
      return;
    }

    STATE.currentAttemptId = data.attempt_id;
    STATE.currentProblem = data.problem;
    STATE.originalBuggyCode = data.problem.buggy_code;
    STATE.currentStageData = data.stage;

    // Switch view and setup workspace
    switchView('workspace');
    setupWorkspace();
  } catch (err) {
    console.error('Failed to start debugging attempt:', err);
  }
}

function setupWorkspace() {
  const prob = STATE.currentProblem;
  document.getElementById('ws-prob-title').textContent = prob.title || 'Debug Challenge';
  document.getElementById('ws-badge-lang').textContent = prob.language.toUpperCase();
  document.getElementById('ws-badge-diff').textContent = prob.difficulty || 'Beginner';
  document.getElementById('ws-badge-concept').textContent = prob.concept || 'Logic';
  document.getElementById('editor-filename').textContent = `solution.${prob.language === 'python' ? 'py' : prob.language}`;

  // Set code in editor
  const editor = document.getElementById('code-editor');
  editor.value = STATE.currentStageData.current_code || prob.buggy_code;
  updateLineNumbers();

  // Reset console
  document.getElementById('console-content').innerHTML = `
    <div class="console-placeholder">
      Click <strong>Run & Verify Code</strong> to compile and execute your solution in the safe sandbox against test cases.
    </div>
  `;

  renderStage(STATE.currentStageData);
}

function renderStage(stage) {
  STATE.currentStageData = stage;
  const stageNum = stage.stage_number;

  // Update Stepper UI
  document.querySelectorAll('.step-item').forEach(item => {
    const s = parseInt(item.dataset.stage, 10);
    item.classList.remove('active', 'completed');
    if (s === stageNum) {
      item.classList.add('active');
    } else if (s < stageNum) {
      item.classList.add('completed');
    }
  });

  // Update Badges & Labels
  document.getElementById('ws-badge-hints').textContent = `Hints Used: ${stage.hints_used || 0}`;
  document.getElementById('stage-badge-pill').textContent = `Stage ${stageNum} of 8`;
  document.getElementById('stage-header-title').textContent = stage.instruction || `Stage ${stageNum}`;
  document.getElementById('ai-provider-label').textContent = stage.ai_label || 'Pedagogical Engine';

  // Populate Stage Body & Footer
  const body = document.getElementById('stage-body');
  const footer = document.getElementById('stage-card-footer');
  body.innerHTML = '';
  footer.innerHTML = '';

  if (stageNum === 1) {
    // Stage 1: Understand
    body.innerHTML = `
      <div class="prompt-box">
        <strong>Task:</strong> ${escapeHtml(stage.prompt)}
      </div>
      <h4>Predict Program Output:</h4>
      <p class="text-sm text-secondary">${escapeHtml(stage.question || '')}</p>
      <div class="options-list" id="stage1-options">
        ${(stage.options || []).map((opt, i) => `
          <button class="option-btn" data-index="${i}" onclick="selectPredictionOption(${i})">
            ${i + 1}. ${escapeHtml(opt)}
          </button>
        `).join('')}
      </div>
      <div id="prediction-feedback" style="display: none; margin-top: 12px;"></div>
    `;

    footer.innerHTML = `
      <button class="btn btn-subtle btn-sm" onclick="requestStrongerHint()">Skip to Hint &rarr;</button>
      <button class="btn btn-primary" id="btn-submit-predict" onclick="submitPrediction(${stage.correct_option_index})" disabled>
        Submit Prediction &rarr;
      </button>
    `;
  } else if (stageNum === 2) {
    // Stage 2: Investigate
    body.innerHTML = `
      <div class="prompt-box">
        <strong>Investigate:</strong> ${escapeHtml(stage.prompt)}
      </div>
      <h4>Identify Suspicious Code Line:</h4>
      <p class="text-sm text-secondary">Which line of code do you think contains the root bug?</p>
      <div class="form-group" style="margin-top: 12px;">
        <label for="input-suspicious-line">Suspicious Line Number:</label>
        <input type="number" id="input-suspicious-line" value="${stage.suspicious_line || 4}" min="1" max="100" style="width: 120px;">
      </div>
      <div class="form-group">
        <label for="input-investigate-reason">Why is this line suspicious? (Optional)</label>
        <input type="text" id="input-investigate-reason" placeholder="e.g. Loop condition exceeds boundary">
      </div>
    `;

    footer.innerHTML = `
      <button class="btn btn-subtle btn-sm" onclick="jumpToStage(1)">&larr; Back</button>
      <div class="flex-center gap-2">
        <button class="btn btn-subtle btn-sm" onclick="requestStrongerHint()">I'm Stuck, Give Me a Hint</button>
        <button class="btn btn-primary" onclick="submitInvestigation()">
          Confirm & Get Hint &rarr;
        </button>
      </div>
    `;
  } else if (stageNum === 3) {
    // Stage 3: First Hint
    body.innerHTML = `
      <div class="hint-box">
        <h4>First Clue:</h4>
        <p>${escapeHtml(stage.hint || '')}</p>
      </div>
      <p class="text-sm text-secondary">
        Now that you have a clue, can you spot the fix in the code editor on the right?
      </p>
    `;

    footer.innerHTML = `
      <button class="btn btn-subtle btn-sm" onclick="requestStrongerHint()">Need a Stronger Hint?</button>
      <button class="btn btn-primary" onclick="jumpToStage(5)">
        I'm Ready to Fix Code &rarr;
      </button>
    `;
  } else if (stageNum === 4) {
    // Stage 4: Stronger Hint
    body.innerHTML = `
      <div class="hint-box" style="border-left-color: #ef4444;">
        <h4>Targeted Clue (Stronger Hint):</h4>
        <p>${escapeHtml(stage.hint || '')}</p>
      </div>
      <p class="text-sm text-secondary">
        This targeted clue points directly to the logic or boundary change required.
      </p>
    `;

    footer.innerHTML = `
      <button class="btn btn-subtle btn-sm" onclick="unlockFullSolution()">Give Up & Reveal Solution</button>
      <button class="btn btn-primary" onclick="jumpToStage(5)">
        Apply Fix in Code &rarr;
      </button>
    `;
  } else if (stageNum === 5) {
    // Stage 5: Attempt
    body.innerHTML = `
      <div class="prompt-box">
        <h4>Write Your Correction:</h4>
        <p>${escapeHtml(stage.prompt || 'Edit the code on the right and click Run & Verify Code.')}</p>
      </div>
      <ul style="padding-left: 20px; font-size: 0.85rem; color: var(--text-secondary); line-height: 1.8;">
        <li>Edit the code directly in the editor on the right.</li>
        <li>Click <strong>Run & Verify Code</strong> to test in the isolated execution sandbox.</li>
        <li>Passing all test cases will automatically record your progress into your Debugging DNA!</li>
      </ul>
    `;

    footer.innerHTML = `
      <button class="btn btn-subtle btn-sm" onclick="requestStrongerHint()">Still Stuck? Get Hint</button>
      <button class="btn btn-success" onclick="runAndVerifyCode()">
        Run & Verify Code &rarr;
      </button>
    `;
  } else if (stageNum === 6) {
    // Stage 6: Verification
    const isSolved = stage.verification_status === 'verified';
    body.innerHTML = `
      <div class="${isSolved ? 'explanation-box' : 'hint-box'}">
        <h4>${isSolved ? 'Verification Successful!' : 'Verification Incomplete'}</h4>
        <p>${isSolved ? 'All test cases passed verified execution!' : 'Some test cases did not pass. Check the execution console.'}</p>
      </div>
    `;

    footer.innerHTML = `
      <button class="btn btn-secondary btn-sm" onclick="jumpToStage(5)">Edit Code Again</button>
      ${isSolved ? '<button class="btn btn-primary" onclick="jumpToStage(7)">Read Explanation & Takeaways &rarr;</button>' : ''}
    `;
  } else if (stageNum === 7) {
    // Stage 7: Explanation
    body.innerHTML = `
      <div class="explanation-box">
        <h4>Conceptual Breakdown:</h4>
        <p>${escapeHtml(stage.explanation || '')}</p>
      </div>
      <h4>Key Takeaway:</h4>
      <p class="text-sm text-secondary">${escapeHtml(stage.takeaway || '')}</p>
    `;

    footer.innerHTML = `
      <button class="btn btn-secondary btn-sm" onclick="switchView('dashboard')">View Updated DNA Dashboard</button>
      <button class="btn btn-primary" onclick="jumpToStage(8)">View Annotated Solution &rarr;</button>
    `;
  } else if (stageNum === 8) {
    // Stage 8: Solution
    body.innerHTML = `
      <div class="explanation-box">
        <h4>Complete Solution Code:</h4>
        <pre style="background: #080d18; padding: 12px; border-radius: 6px; font-family: var(--font-mono); font-size: 0.85rem; overflow-x: auto; color: #34d399;"><code>${escapeHtml(stage.solution_code || '')}</code></pre>
      </div>
    `;

    footer.innerHTML = `
      <button class="btn btn-secondary btn-sm" onclick="switchView('catalog')">Try Another Problem</button>
      <button class="btn btn-primary" onclick="switchView('dashboard')">Back to DNA Dashboard</button>
    `;
  }
}

// Stage 1 Quiz Selection
let selectedPredictionIdx = null;
function selectPredictionOption(idx) {
  selectedPredictionIdx = idx;
  document.querySelectorAll('#stage1-options .option-btn').forEach((btn, i) => {
    btn.classList.toggle('selected', i === idx);
  });
  const subBtn = document.getElementById('btn-submit-predict');
  if (subBtn) subBtn.disabled = false;
}

async function submitPrediction(correctIdx) {
  const isCorrect = (selectedPredictionIdx === correctIdx);
  const fb = document.getElementById('prediction-feedback');
  fb.style.display = 'block';
  fb.className = isCorrect ? 'badge badge-diff' : 'badge badge-hints';
  fb.textContent = isCorrect
    ? 'Correct prediction! You identified the abnormal behavior.'
    : 'Not quite, but good try! Let us investigate line by line.';

  setTimeout(async () => {
    const res = await fetch(`/api/attempts/${STATE.currentAttemptId}/interact`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        action: 'submit_prediction',
        user_input: `Selected Option ${selectedPredictionIdx}`,
        lang: STATE.language
      })
    });
    const nextStage = await res.json();
    renderStage(nextStage);
  }, 1000);
}

async function submitInvestigation() {
  const line = document.getElementById('input-suspicious-line').value;
  const reason = document.getElementById('input-investigate-reason').value;

  const res = await fetch(`/api/attempts/${STATE.currentAttemptId}/interact`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      action: 'submit_investigation',
      user_input: `Line ${line}: ${reason}`,
      lang: STATE.language
    })
  });
  const nextStage = await res.json();
  renderStage(nextStage);
}

async function requestStrongerHint() {
  const res = await fetch(`/api/attempts/${STATE.currentAttemptId}/interact`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      action: 'request_hint',
      user_input: 'Requested progressive hint',
      lang: STATE.language
    })
  });
  const nextStage = await res.json();
  renderStage(nextStage);
}

async function jumpToStage(stageNum) {
  const res = await fetch(`/api/attempts/${STATE.currentAttemptId}/stage`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      stage: stageNum,
      lang: STATE.language
    })
  });
  const nextStage = await res.json();
  renderStage(nextStage);
}

async function unlockFullSolution() {
  if (!confirm('Are you sure you want to reveal the full solution? We recommend trying one more hint first!')) {
    return;
  }
  const res = await fetch(`/api/attempts/${STATE.currentAttemptId}/interact`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      action: 'unlock_solution',
      user_input: 'Unlocked solution',
      lang: STATE.language
    })
  });
  const nextStage = await res.json();
  renderStage(nextStage);
}

async function reloadCurrentStage() {
  if (!STATE.currentAttemptId) return;
  const stageNum = STATE.currentStageData ? STATE.currentStageData.stage_number : 1;
  await jumpToStage(stageNum);
}

// ==================== CODE EXECUTION & VERIFICATION ====================
async function runAndVerifyCode() {
  const code = document.getElementById('code-editor').value;
  const consoleEl = document.getElementById('console-content');

  if (!code || !code.trim()) {
    consoleEl.innerHTML = `
      <div class="test-suite-summary failed">
        <span>Code submission is empty</span>
        <span>0 / 1 Tests Run</span>
      </div>
      <div style="color: #ef4444; font-family: var(--font-mono); font-size: 0.85rem; padding: 8px;">
        Please enter or write your code in the editor above before clicking Run & Verify.
      </div>
    `;
    return;
  }

  consoleEl.innerHTML = `
    <div class="flex-center gap-2" style="color: var(--accent-primary);">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="spin"><circle cx="12" cy="12" r="10"/><path d="M12 2a10 10 0 0 1 10 10"/></svg>
      Compiling and verifying execution in isolated sandbox...
    </div>
  `;

  try {
    const res = await fetch(`/api/attempts/${STATE.currentAttemptId}/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        code: code,
        lang: STATE.language
      })
    });
    const result = await res.json();
    renderExecutionResults(result);

    // Refresh stage data to reflect solved status or verification state
    if (result.next_stage_data) {
      renderStage(result.next_stage_data);
    }
  } catch (err) {
    consoleEl.innerHTML = `<div class="text-danger">Execution error: ${err.message}</div>`;
  }
}

function renderExecutionResults(verifyResult) {
  const consoleEl = document.getElementById('console-content');
  const exec = verifyResult.execution_result || {};

  // Check compile error
  if (!exec.is_compiled) {
    consoleEl.innerHTML = `
      <div class="test-suite-summary failed">
        <span>Compilation Failed</span>
        <span>0 / ${exec.total_tests || 1} Tests Run</span>
      </div>
      <div style="color: #ef4444; font-family: var(--font-mono); white-space: pre-wrap; font-size: 0.8rem;">
        ${escapeHtml(exec.compile_error || 'Compilation Error')}
      </div>
    `;
    return;
  }

  const allPassed = exec.all_passed;
  let testHtml = `
    <div class="test-suite-summary ${allPassed ? 'all-passed' : 'failed'}">
      <span>${allPassed ? '✓ All Test Cases Passed (Verified Execution)' : '✕ Some Test Cases Failed'}</span>
      <span>${exec.passed_tests} / ${exec.total_tests} Passed</span>
    </div>
  `;

  (exec.test_results || []).forEach((tc, idx) => {
    testHtml += `
      <div class="test-case-card">
        <div class="test-case-header">
          <strong>Test Case #${idx + 1}: ${escapeHtml(tc.description || 'Sample Test')}</strong>
          <span class="${tc.passed ? 'text-success' : 'text-danger'}" style="font-weight: 600;">
            ${tc.passed ? 'PASSED' : 'FAILED'} (${tc.duration_ms}ms)
          </span>
        </div>
        ${tc.expected_output ? `
          <div class="test-case-row">
            <span>Expected:</span>
            <span class="val font-mono">${escapeHtml(tc.expected_output.trim())}</span>
          </div>
        ` : ''}
        <div class="test-case-row">
          <span>Actual Output:</span>
          <span class="val font-mono">${escapeHtml(tc.actual_output.trim() || '[No Output]')}</span>
        </div>
        ${tc.error ? `
          <div class="test-case-row" style="color: #ef4444; margin-top: 4px;">
            <span>Error:</span>
            <span class="val">${escapeHtml(tc.error)}</span>
          </div>
        ` : ''}
      </div>
    `;
  });

  consoleEl.innerHTML = testHtml;
}

function resetEditorCode() {
  if (confirm('Reset code to the original buggy starting state?')) {
    document.getElementById('code-editor').value = STATE.originalBuggyCode;
    updateLineNumbers();
  }
}

// ==================== CODE EDITOR HELPERS ====================
function updateLineNumbers() {
  const editor = document.getElementById('code-editor');
  const lineNumbers = document.getElementById('line-numbers');
  const lines = editor.value.split('\n').length;
  let html = '';
  for (let i = 1; i <= Math.max(lines, 1); i++) {
    html += `${i}<br>`;
  }
  lineNumbers.innerHTML = html;
}

function syncEditorScroll() {
  const editor = document.getElementById('code-editor');
  const lineNumbers = document.getElementById('line-numbers');
  lineNumbers.scrollTop = editor.scrollTop;
}

function handleEditorKeyDown(e) {
  if (e.key === 'Tab') {
    e.preventDefault();
    const start = this.selectionStart;
    const end = this.selectionEnd;
    this.value = this.value.substring(0, start) + '    ' + this.value.substring(end);
    this.selectionStart = this.selectionEnd = start + 4;
    updateLineNumbers();
  }
}

// ==================== FEATURE 4: CUSTOM CODE DIAGNOSTICS ====================
async function handleCustomDebugSubmit(e) {
  e.preventDefault();
  const lang = document.getElementById('custom-lang').value;
  const title = document.getElementById('custom-title').value;
  const error = document.getElementById('custom-error').value;
  const code = document.getElementById('custom-code').value;

  try {
    const res = await fetch('/api/custom-debug', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: STATE.userId,
        language: lang,
        code: code,
        title: title,
        description: `${title} ${error}`.trim(),
        lang: STATE.language
      })
    });
    const data = await res.json();
    if (data.error) {
      alert(`Error: ${data.error}`);
      return;
    }

    STATE.currentAttemptId = data.attempt_id;
    STATE.currentProblem = {
      title: title || 'Custom Snippet',
      language: lang,
      difficulty: 'Custom',
      concept: data.classification ? data.classification.primary_category.replace(/_/g, ' ') : 'General Logic',
      buggy_code: code
    };
    STATE.originalBuggyCode = code;
    STATE.currentStageData = data.stage;

    switchView('workspace');
    setupWorkspace();
  } catch (err) {
    console.error('Failed to analyze custom code:', err);
  }
}

// ==================== USER REGISTRATION ====================
function showRegisterModal() {
  document.getElementById('modal-register').classList.add('active');
}

function hideRegisterModal() {
  document.getElementById('modal-register').classList.remove('active');
  document.getElementById('user-select').value = STATE.userId;
}

async function handleRegisterSubmit(e) {
  e.preventDefault();
  const username = document.getElementById('reg-username').value.trim();
  const displayName = document.getElementById('reg-display-name').value.trim();
  const password = document.getElementById('reg-password').value.trim();

  try {
    const res = await fetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: username,
        display_name: displayName,
        password: password
      })
    });
    const data = await res.json();
    if (data.error) {
      alert(`Registration error: ${data.error}`);
      return;
    }

    hideRegisterModal();
    await loadUsers();
    STATE.userId = data.user.id;
    document.getElementById('user-select').value = STATE.userId;
    await loadStudentDNA();
    switchView('dashboard');
  } catch (err) {
    console.error('Registration failed:', err);
  }
}

// ==================== UTILITIES ====================
function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// Expose functions for inline HTML event handlers
window.startDebuggingProblem = startDebuggingProblem;
window.selectPredictionOption = selectPredictionOption;
window.submitPrediction = submitPrediction;
window.submitInvestigation = submitInvestigation;
window.requestStrongerHint = requestStrongerHint;
window.jumpToStage = jumpToStage;
window.unlockFullSolution = unlockFullSolution;
window.runAndVerifyCode = runAndVerifyCode;
window.resetEditorCode = resetEditorCode;
window.switchView = switchView;

