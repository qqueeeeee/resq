const state = {
  data: null,
  modes: [],
  hotkeys: null,
  launch: null,
};

const els = {};

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  bindEls();
  setLoading(true);
});

window.addEventListener('pywebviewready', async () => {
  await loadState();
});

function bindEls() {
  els.loader = document.querySelector('#loader');
  els.currentMode = document.querySelector('#current-mode');
  els.riskBadge = document.querySelector('#risk-badge');
  els.applySafeBtn = document.querySelector('#apply-safe');
  els.revertBtn = document.querySelector('#revert');
  els.safeMode = document.querySelector('#safe-mode');
  els.safeMsg = document.querySelector('#safe-msg');
  els.useCurrentBtn = document.querySelector('#use-current');
  els.applySelectedSafeBtn = document.querySelector('#apply-selected-safe');
  els.presetList = document.querySelector('#preset-list');
  els.presetMsg = document.querySelector('#preset-msg');
  els.hotkeyList = document.querySelector('#hotkey-list');
  els.hotkeyMsg = document.querySelector('#hotkey-msg');
  els.guardMsg = document.querySelector('#guard-msg');
  els.guardToggle = document.querySelector('#guard-toggle');
  els.countdown = document.querySelector('#countdown');
  els.countdownValue = document.querySelector('#countdown-value');
  els.launchMsg = document.querySelector('#launch-msg');
  els.runStartupToggle = document.querySelector('#run-startup');
  els.minimizeTrayToggle = document.querySelector('#minimize-tray');

  els.applySafeBtn.addEventListener('click', () => applySafeFallback(els.applySafeBtn));
  els.applySelectedSafeBtn.addEventListener('click', () => applySafeFallback(els.applySelectedSafeBtn));
  els.revertBtn.addEventListener('click', revertMode);
  els.useCurrentBtn.addEventListener('click', useCurrentAsSafe);
  els.safeMode.addEventListener('change', setSafeFromSelect);
  els.guardToggle.addEventListener('click', toggleGuard);
  els.countdown.addEventListener('input', () => {
    els.countdownValue.textContent = els.countdown.value;
  });
  els.countdown.addEventListener('change', saveGuard);
  els.runStartupToggle.addEventListener('click', toggleRunOnStartup);
  els.minimizeTrayToggle.addEventListener('click', toggleMinimizeToTray);
}

function initTheme() {
  const saved = getSavedTheme();
  document.documentElement.dataset.theme = saved;
}

function getSavedTheme() {
  try {
    return localStorage.getItem('resq-theme') || 'light';
  } catch (_) {
    return 'light';
  }
}

async function loadState() {
  const [res, hotkeysRes, launchRes] = await Promise.all([
    api().get_state(),
    api().get_hotkeys(),
    api().get_launch_settings(),
  ]);
  if (!res.ok) {
    showMsg(els.guardMsg, res.error);
    return;
  }

  state.data = res;
  state.modes = res.supported_modes;
  if (hotkeysRes && hotkeysRes.ok) {
    state.hotkeys = hotkeysRes.hotkeys;
  } else {
    console.error('get_hotkeys failed', hotkeysRes);
    state.hotkeys = {
      safe: '--',
      preset1: '--',
      preset2: '--',
      preset3: '--',
      settings: '--',
    };
  }
  if (launchRes && launchRes.ok) {
    state.launch = launchRes;
  } else {
    console.error('get_launch_settings failed', launchRes);
    state.launch = {
      run_on_startup: false,
      minimize_to_tray: false,
    };
  }
  setLoading(false);
  els.loader.classList.add('hidden');
  render();
}

function render() {
  renderCurrent();
  renderSafe();
  renderPresets();
  renderHotkeys();
  renderGuard();
  renderLaunch();
}

function renderCurrent() {
  const current = state.data.current;
  const match = state.data.presets.find((p) => sameMode(p, current));
  const isRisky = match && !match.is_safe;

  els.currentMode.textContent = formatMode(current);
  els.riskBadge.className = 'badge';

  if (isRisky) {
    els.riskBadge.textContent = 'risky';
    els.riskBadge.classList.add('risky');
  } else if (match || sameMode(state.data.safe, current)) {
    els.riskBadge.textContent = 'normal';
    els.riskBadge.classList.add('normal');
  } else {
    els.riskBadge.textContent = 'unmarked';
    els.riskBadge.classList.add('unmarked');
  }
}

function renderSafe() {
  fillModes(els.safeMode);
  els.safeMode.value = modeValue(state.data.safe);
}

function renderPresets() {
  els.presetList.innerHTML = '';

  state.data.presets.forEach((preset) => {
    const row = document.createElement('div');
    row.className = `preset-row ${sameMode(preset, state.data.current) ? 'active' : ''}`;
    row.dataset.slot = preset.slot;

    row.innerHTML = `
      <div class="slot">${preset.slot}</div>
      <input class="preset-name" type="text" value="${escapeAttr(preset.name || '')}" aria-label="preset name">
      <select class="preset-mode" aria-label="preset mode"></select>
      <button class="toggle ${preset.is_safe ? '' : 'on'}" aria-label="risky preset toggle"></button>
      <button class="link-btn capture">capture</button>
      <button class="btn apply">apply</button>
    `;

    const select = row.querySelector('.preset-mode');
    fillModes(select);
    select.value = modeValue(preset);

    row.querySelector('.preset-name').addEventListener('blur', () => savePreset(row));
    row.querySelector('.preset-name').addEventListener('keydown', (e) => {
      if (e.key === 'Enter') e.currentTarget.blur();
    });
    select.addEventListener('change', () => savePreset(row));
    row.querySelector('.toggle').addEventListener('click', async (e) => {
      e.currentTarget.classList.toggle('on');
      await savePreset(row);
    });
    row.querySelector('.capture').addEventListener('click', () => capturePreset(row));
    row.querySelector('.apply').addEventListener('click', () => applyPreset(row));

    els.presetList.appendChild(row);
  });
}

function renderGuard() {
  els.guardToggle.classList.toggle('on', state.data.guard.enabled);
  els.guardToggle.classList.add('safe');
  els.countdown.value = state.data.guard.countdown_seconds;
  els.countdownValue.textContent = state.data.guard.countdown_seconds;
}

function renderHotkeys() {
  const rows = [
    ['safe', 'safe resolution'],
    ['preset1', 'preset 1'],
    ['preset2', 'preset 2'],
    ['preset3', 'preset 3'],
    ['settings', 'open settings'],
  ];

  els.hotkeyList.innerHTML = '';
  rows.forEach(([action, label]) => {
    const item = document.createElement('div');
    const value = state.hotkeys ? (state.hotkeys[action] || '--') : '--';
    item.className = 'hotkey-item';
    item.innerHTML = `
      <div class="hotkey-row">
        <span>${label}</span>
        <input class="hotkey-input" type="text" value="${escapeAttr(value)}" data-action="${action}" aria-label="${label} hotkey">
      </div>
      <div class="row-error"></div>
    `;

    const input = item.querySelector('.hotkey-input');
    input.dataset.prev = value;
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') e.currentTarget.blur();
    });
    input.addEventListener('blur', () => saveHotkey(input, item.querySelector('.row-error')));
    els.hotkeyList.appendChild(item);
  });
}

function renderLaunch() {
  els.runStartupToggle.classList.toggle('on', Boolean(state.launch && state.launch.run_on_startup));
  els.minimizeTrayToggle.classList.toggle('on', Boolean(state.launch && state.launch.minimize_to_tray));
}

async function setSafeFromSelect() {
  const mode = parseModeValue(els.safeMode.value);
  const res = await api().set_safe_mode(mode.width, mode.height, mode.frequency);
  handleResult(res, els.safeMsg, els.safeMode);
  if (res.ok) await loadState();
}

async function applySafeFallback(target) {
  const mode = parseModeValue(els.safeMode.value);
  const res = await api().apply_mode(mode.width, mode.height, mode.frequency);
  handleResult(res, els.safeMsg, target);
  if (res.ok) await loadState();
}

async function useCurrentAsSafe() {
  const res = await api().use_current_as_safe();
  handleResult(res, els.safeMsg, els.useCurrentBtn);
  if (res.ok) await loadState();
}

async function savePreset(row) {
  const mode = parseModeValue(row.querySelector('.preset-mode').value);
  const name = row.querySelector('.preset-name').value;
  const isSafe = !row.querySelector('.toggle').classList.contains('on');
  const slot = Number(row.dataset.slot);

  const res = await api().save_preset(slot, name, mode.width, mode.height, mode.frequency, isSafe);
  handleResult(res, els.presetMsg, row);
  if (res.ok) await loadState();
}

async function capturePreset(row) {
  const res = await api().capture_preset(Number(row.dataset.slot));
  handleResult(res, els.presetMsg, row.querySelector('.capture'));
  if (res.ok) await loadState();
}

async function applyPreset(row) {
  const mode = parseModeValue(row.querySelector('.preset-mode').value);
  const res = await api().apply_mode(mode.width, mode.height, mode.frequency);
  handleResult(res, els.presetMsg, row.querySelector('.apply'));
  if (res.ok) await loadState();
}

async function toggleGuard() {
  els.guardToggle.classList.toggle('on');
  await saveGuard();
}

async function saveGuard() {
  const enabled = els.guardToggle.classList.contains('on');
  const seconds = Number(els.countdown.value);
  const res = await api().set_guard(enabled, seconds);
  handleResult(res, els.guardMsg, els.guardToggle);
  if (res.ok) await loadState();
}

async function saveHotkey(input, msgEl) {
  const next = input.value.trim();
  const prev = input.dataset.prev || '';
  if (next === prev) return;

  const res = await api().set_hotkey(input.dataset.action, next);
  if (!res.ok) {
    input.value = prev;
    showRowError(msgEl, res.error);
    return;
  }

  input.dataset.prev = next;
  flash(input);
}

async function toggleRunOnStartup() {
  els.runStartupToggle.classList.toggle('on');
  const enabled = els.runStartupToggle.classList.contains('on');
  const res = await api().set_run_on_startup(enabled);
  if (!res.ok) {
    els.runStartupToggle.classList.toggle('on', !enabled);
    showMsg(els.launchMsg, res.error);
    return;
  }
  flash(els.runStartupToggle);
}

async function toggleMinimizeToTray() {
  els.minimizeTrayToggle.classList.toggle('on');
  const enabled = els.minimizeTrayToggle.classList.contains('on');
  const res = await api().set_minimize_to_tray(enabled);
  if (!res.ok) {
    els.minimizeTrayToggle.classList.toggle('on', !enabled);
    showMsg(els.launchMsg, res.error);
    return;
  }
  flash(els.minimizeTrayToggle);
}

async function revertMode() {
  const res = await api().revert();
  handleResult(res, els.guardMsg, els.revertBtn);
  if (res.ok) await loadState();
}

function handleResult(res, msgEl, flashEl) {
  if (!res.ok) {
    showMsg(msgEl, res.error);
    return;
  }
  showMsg(msgEl, 'saved', true);
  flash(flashEl);
}

function showMsg(el, text, ok = false) {
  el.textContent = text || '';
  el.classList.toggle('ok', ok);
  clearTimeout(el._timer);
  el._timer = setTimeout(() => {
    el.textContent = '';
    el.classList.remove('ok');
  }, 3000);
}

function showRowError(el, text) {
  el.textContent = text || '';
  clearTimeout(el._timer);
  el._timer = setTimeout(() => {
    el.textContent = '';
  }, 3000);
}

function flash(el) {
  if (!el) return;
  el.classList.add('flash');
  setTimeout(() => el.classList.remove('flash'), 1000);
}

function fillModes(select) {
  select.innerHTML = '';
  state.modes.forEach((mode) => {
    const option = document.createElement('option');
    option.value = modeValue(mode);
    option.textContent = formatOption(mode);
    select.appendChild(option);
  });
}

function formatMode(mode) {
  return `${mode.width} × ${mode.height} @ ${mode.frequency}Hz`;
}

function formatOption(mode) {
  return `${mode.width}x${mode.height} @ ${mode.frequency}Hz`;
}

function modeValue(mode) {
  return `${mode.width}x${mode.height}@${mode.frequency}`;
}

function parseModeValue(value) {
  const match = String(value).match(/(\d+)x(\d+)@(\d+)/);
  if (!match) throw new Error(`bad mode: ${value}`);
  return {
    width: Number(match[1]),
    height: Number(match[2]),
    frequency: Number(match[3]),
  };
}

function sameMode(a, b) {
  return a && b && a.width === b.width && a.height === b.height && a.frequency === b.frequency;
}

function setLoading(loading) {
  document.querySelectorAll('button, select, input').forEach((el) => {
    el.disabled = loading;
  });
}

function api() {
  return window.pywebview.api;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

function escapeAttr(value) {
  return escapeHtml(value);
}
