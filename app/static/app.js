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

function tick() {
  const nowMs = Date.now();

  document.querySelectorAll('.idle').forEach(span => {
    const iso = span.dataset.frontsince;
    if (!iso) { span.textContent = '00:00:00'; return; }
    const t0 = new Date(iso).getTime();
    const elapsed = Math.round((nowMs - t0) / 1000);
    span.textContent = fmt(Math.max(0, elapsed));
  });

  document.querySelectorAll('.runline').forEach(el => {
    const endMs = new Date(el.dataset.end).getTime();
    const graceMs = new Date(el.dataset.grace).getTime();
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
tick(); setInterval(tick, 1000);
