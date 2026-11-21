const timeFormatter = new Intl.DateTimeFormat('zh-CN', {timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit',
  day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', fractionalSecondDigits: 3, hourCycle: 'h23'});

document.querySelectorAll('#review [data-ms]').forEach(cell => {
  const value = Number(cell.textContent);
  if (Number.isFinite(value)) cell.textContent = timeFormatter.format(value);
});

async function submitReview(form) {
  const output = form.querySelector('.review-feedback');
  const button = form.querySelector('button[type=submit]');
  const payload = Object.fromEntries(new FormData(form).entries());
  payload.period_start_ms = Number(payload.period_start_ms);
  payload.period_end_ms = Number(payload.period_end_ms);
  button.disabled = true;
  output.classList.remove('error');
  output.textContent = '正在复核并重算…';
  try {
    const response = await fetch(`/api/review/${encodeURIComponent(form.dataset.run)}/notes`, {
      method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.message || '复核失败');
    const target = new URL(location.href);
    target.search = new URLSearchParams({
      run: result.run_id, notice: result.reused ? 'review_reused' : 'reviewed',
    });
    target.hash = '#review';
    location.assign(target);
  } catch (error) {
    output.classList.add('error');
    output.textContent = error.message;
    button.disabled = false;
  }
}

document.querySelectorAll('.review-form').forEach(form => {
  form.addEventListener('submit', event => {
    event.preventDefault();
    submitReview(form);
  });
});
