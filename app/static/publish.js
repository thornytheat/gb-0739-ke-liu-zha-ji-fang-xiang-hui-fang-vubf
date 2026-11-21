export function publishControls() {
  const upload = document.querySelector('#upload');
  const toolbar = document.querySelector('#run-feedback');
  const form = document.querySelector('#upload-form');
  const publishButtons = document.querySelectorAll('[data-publish], #upload-form button[type=submit]');
  let publishing = false;
  async function publish(url, output, body) {
    if (publishing) return;
    publishing = true;
    publishButtons.forEach(button => { button.disabled = true; });
    output.textContent = '正在回放…';
    output.classList.remove('error');
    try {
      const response = await fetch(url, {method: 'POST', body});
      const result = await response.json();
      if (!response.ok) throw new Error(result.message || '请检查提交的文件。');
      const target = new URL(location.href);
      target.search = new URLSearchParams({run: result.run_id, notice: result.reused ? 'reused' : 'published'});
      location.assign(target);
    } catch (error) {
      output.classList.add('error');
      output.textContent = error instanceof TypeError ? '连接失败，请重试。' : error.message;
      publishButtons.forEach(button => { button.disabled = false; });
      publishing = false;
    }
  }
  document.querySelector('#import-open').onclick = () => upload.showModal();
  document.querySelector('#import-close').onclick = () => upload.close();
  document.querySelectorAll('[data-publish]').forEach(button => {
    button.onclick = () => publish(button.dataset.publish, toolbar);
  });
  form.onsubmit = event => {
    event.preventDefault();
    publish('/api/runs', document.querySelector('#upload-feedback'), new FormData(form));
  };
}
