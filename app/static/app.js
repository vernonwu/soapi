function fmt(sec) {
  const sign = sec < 0 ? -1 : 1;
  sec = Math.abs(sec);
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = Math.floor(sec % 60);
  const pad = n => (n < 10 ? '0' + n : '' + n);
  const core = (h > 0 ? h + ':' : '') + pad(m) + ':' + pad(s);
  return (sign < 0 ? '-' : '') + core;
}

const meta = document.getElementById('server-meta');
const serverNowMs = meta ? Number(meta.dataset.serverNowMs) : Date.now();
let clockOffsetMs = Number.isFinite(serverNowMs) ? serverNowMs - Date.now() : 0;
let latestUpdateMs = meta ? Number(meta.dataset.lastUpdateMs) : NaN;
if (!Number.isFinite(latestUpdateMs)) {
  latestUpdateMs = serverNowMs;
}

function tick() {
  const nowMs = Date.now() + clockOffsetMs;

  document.querySelectorAll('.idle').forEach(span => {
    const raw = span.dataset.frontSinceMs;
    const t0 = raw ? Number(raw) : NaN;
    if (!Number.isFinite(t0)) { span.textContent = '00:00:00'; return; }
    const elapsed = Math.round((nowMs - t0) / 1000);
    span.textContent = fmt(Math.max(0, elapsed));
  });

  document.querySelectorAll('.runline').forEach(el => {
    const endMsRaw = el.dataset.endMs;
    const graceMsRaw = el.dataset.graceMs;
    const endMs = endMsRaw ? Number(endMsRaw) : NaN;
    const graceMs = graceMsRaw ? Number(graceMsRaw) : NaN;
    if (!Number.isFinite(endMs) || !Number.isFinite(graceMs)) {
      el.textContent = '--:--';
      return;
    }
    const badge = el.closest('li').querySelector('.state-badge');

    let text = '';
    if (nowMs < endMs) {
      const rem = Math.round((endMs - nowMs) / 1000);
      text = fmt(rem);
      el.style.color = '';
      if (badge) { badge.textContent = 'running'; badge.dataset.state = 'running'; }
    } else if (nowMs < graceMs) {
      const remGrace = Math.round((graceMs - nowMs) / 1000);
      text = fmt(remGrace);
      el.style.color = 'var(--green)';
      if (badge) { badge.textContent = 'awaiting pickup'; badge.dataset.state = 'awaiting'; }
    } else {
      const overdue = -Math.round((nowMs - graceMs) / 1000);
      text = fmt(overdue);
      el.style.color = 'var(--red)';
      if (badge) { badge.textContent = 'overdue'; badge.dataset.state = 'overdue'; }
    }
    el.textContent = text;
  });
}

async function pollUpdates() {
  try {
    const resp = await fetch('/sync-state', { cache: 'no-store' });
    if (!resp.ok) {
      return;
    }
    const data = await resp.json();
    if (Number.isFinite(data.server_now_ms)) {
      clockOffsetMs = data.server_now_ms - Date.now();
    }
    if (Number.isFinite(data.last_update_ms)) {
      if (data.last_update_ms > latestUpdateMs) {
        window.location.reload();
        return;
      }
      latestUpdateMs = Math.max(latestUpdateMs, data.last_update_ms);
    }
  } catch (err) {
    // swallow network errors; next poll will retry
  }
}

tick();
setInterval(tick, 1000);
setTimeout(pollUpdates, 1500);
setInterval(pollUpdates, 3000);
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible') {
    pollUpdates();
  }
});
