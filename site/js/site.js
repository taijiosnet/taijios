// Page behaviour: the Run button, boot progress, fullscreen and the theme.
import { startTaiji } from './taiji-emu.js';

const root = document.documentElement;
const run = document.getElementById('run');
const stage = document.getElementById('stage');
const canvas = document.getElementById('taiji-screen');
const progress = document.getElementById('boot-progress');
const bar = document.getElementById('boot-bar');
const status = document.getElementById('boot-status');
const fullscreen = document.getElementById('fullscreen');

const words = {
  loading: 'Downloading TaijiOS',
  starting: 'Starting the Inferno emulator',
  running: 'Rill desktop running',
};

function setState(state, detail = '') {
  root.dataset.taiji = state;
  if (status) status.textContent = detail || words[state] || state;
}

function megabytes(bytes) {
  return (bytes / 1048576).toFixed(1);
}

async function boot() {
  if (root.dataset.taiji) return;
  stage.classList.add('is-booting');
  stage.scrollIntoView({ behavior: 'smooth', block: 'center' });
  setState('loading');
  try {
    await startTaiji(canvas, {
      onProgress(received, total) {
        bar.style.width = `${Math.min(100, (100 * received) / total).toFixed(1)}%`;
        status.textContent = `${words.loading}: ${megabytes(received)} of ${megabytes(total)} MB`;
      },
      onStatus(state) {
        if (state === 'running') stage.classList.add('is-running');
        setState(state);
      },
    });
  } catch (error) {
    console.error(error);
    stage.classList.add('is-failed');
    setState('error', `Could not start TaijiOS: ${error.message}`);
  }
}

run.addEventListener('click', boot);
for (const link of document.querySelectorAll('[data-run]')) {
  link.addEventListener('click', (event) => { event.preventDefault(); boot(); });
}

fullscreen.addEventListener('click', () => {
  if (document.fullscreenElement) document.exitFullscreen();
  else stage.requestFullscreen().catch(() => {});
});

// Light, dark or the system's choice, remembered on this device.
const themeButton = document.getElementById('theme');
function applyTheme(theme) {
  if (theme) root.dataset.theme = theme;
  else delete root.dataset.theme;
}
try { applyTheme(localStorage.getItem('taiji-theme')); } catch (error) { /* storage unavailable */ }
themeButton.addEventListener('click', () => {
  const dark = root.dataset.theme ? root.dataset.theme === 'dark'
    : matchMedia('(prefers-color-scheme: dark)').matches;
  const next = dark ? 'light' : 'dark';
  applyTheme(next);
  try { localStorage.setItem('taiji-theme', next); } catch (error) { /* storage unavailable */ }
});

if (new URLSearchParams(location.search).has('run')) boot();
