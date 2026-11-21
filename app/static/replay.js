import {sections} from './descriptors.js';
import {publishControls} from './publish.js';

const $ = selector => document.querySelector(selector);
const view = $('#view');
const station = $('#station');
const search = $('#search');
const feedback = $('#evidence-feedback');
const previous = $('#previous');
const more = $('#more');
const run = document.body.dataset.run;
const limit = 18;
let active = 'direction';
let offset = 0;
let currentRequest;

const times = new Intl.DateTimeFormat('zh-CN', {timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit',
  day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', fractionalSecondDigits: 3, hourCycle: 'h23'});
const integer = new Intl.NumberFormat('zh-CN');
const numeric = new Set(['ms', 'number', 'line']);

function format(value, type, row) {
  if (value === undefined || value === null || value === '') return '—';
  if (type === 'ms') return times.format(value);
  if (type === 'number') return integer.format(value);
  if (type === 'bool') return value ? '允许' : '禁用';
  if (type === 'line' && row.last_line !== value) return `${value}–${row.last_line}`;
  return String(value);
}

function detail(value, type, row) {
  const details = document.createElement('details');
  const summary = document.createElement('summary');
  const body = document.createElement('pre');
  summary.textContent = type === 'pulses' ? `${value.length} 次触发` : '查看';
  if (type === 'pulses') {
    body.textContent = value.map(pulse => `${pulse.beam}  ${pulse.pulse}\n${times.format(pulse.corrected_ms)} · 源行 ${pulse.line} · 偏移行 ${pulse.offset_line}`).join('\n\n');
  } else {
    const extra = row.detail && Object.keys(row.detail).length ? `\n${JSON.stringify(row.detail, null, 2)}` : '';
    body.textContent = JSON.stringify(value, null, 2) + extra;
  }
  details.append(summary, body);
  return details;
}

function table(columns, rows, empty, failed = false) {
  const head = document.createElement('tr');
  for (const [, text, type] of columns) {
    const label = document.createElement('th');
    label.scope = 'col';
    label.textContent = text;
    if (numeric.has(type)) label.className = 'num';
    head.append(label);
  }
  $('#cols').replaceChildren(head);
  const body = $('#rows');
  body.replaceChildren();
  if (!rows.length) {
    const cell = body.insertRow().insertCell();
    cell.colSpan = columns.length;
    cell.className = failed ? 'empty error' : 'empty';
    cell.textContent = empty;
  }
  for (const row of rows) {
    const tr = body.insertRow();
    for (const [key, , type] of columns) {
      const cell = tr.insertCell();
      if (numeric.has(type)) cell.className = 'num';
      if (['pulses', 'detail'].includes(type) && Array.isArray(row[key])) {
        cell.append(detail(row[key], type, row));
      } else {
        const span = document.createElement('span');
        span.textContent = format(row[key], type, row);
        span.title = span.textContent;
        cell.append(span);
      }
    }
  }
}

async function load() {
  currentRequest?.abort();
  const request = new AbortController();
  currentRequest = request;
  const [, columns] = sections[active][view.value];
  const params = new URLSearchParams({view: view.value, station: station.value, q: search.value, offset, limit});
  feedback.textContent = '读取中…';
  previous.disabled = more.disabled = true;
  table(columns, [], '正在读取证据…');
  try {
    const response = await fetch(`/api/${active}/${encodeURIComponent(run)}?${params}`, {signal: request.signal});
    if (!response.ok) throw new Error('读取失败');
    const data = await response.json();
    if (currentRequest !== request) return;
    table(columns, data.items, '无匹配证据，请调整筛选。');
    feedback.textContent = `${data.total} 条${data.items.length ? ` · ${offset + 1}–${offset + data.items.length}` : ''}`;
    previous.disabled = offset === 0;
    more.disabled = offset + limit >= data.total;
  } catch (error) {
    if (error.name === 'AbortError' || currentRequest !== request) return;
    feedback.textContent = '证据读取失败';
    table(columns, [], '读取失败，请重新筛选。', true);
  }
}

function switchSection(module, initialView = 'main', term = '') {
  active = module;
  view.replaceChildren(...Object.entries(sections[module]).map(([key, [text]]) => new Option(text, key)));
  view.value = initialView;
  search.value = term;
  station.value = '';
  offset = 0;
  document.querySelectorAll('nav [data-module]').forEach(link => {
    if (link.dataset.module === module) {
      link.setAttribute('aria-current', 'location');
      $('#module-title').textContent = link.textContent.trim();
    } else link.removeAttribute('aria-current');
  });
  document.querySelectorAll('[data-event]').forEach(row => row.classList.toggle('selected', row.dataset.event === term));
  load();
}

function openEvidence(module, initialView, term) {
  history.replaceState(null, '', `#${module}`);
  switchSection(module, initialView, term);
  $('#proof').scrollIntoView({block: 'nearest'});
}

for (const link of document.querySelectorAll('[data-module]')) {
  link.addEventListener('click', event => {
    event.preventDefault();
    openEvidence(link.dataset.module, link.dataset.view || 'main');
  });
}
for (const button of document.querySelectorAll('[data-encounter], [data-anchor]')) {
  button.addEventListener('click', () => {
    if (button.dataset.anchor) openEvidence('transfer', 'anchors', button.dataset.anchor);
    else openEvidence('direction', 'main', button.dataset.encounter);
  });
}
$('#filters').addEventListener('submit', event => { event.preventDefault(); offset = 0; load(); });
[view, station].forEach(control => control.addEventListener('change', () => { offset = 0; load(); }));
previous.onclick = () => { offset = Math.max(offset - limit, 0); load(); };
more.onclick = () => { offset += limit; load(); };
const initial = location.hash.slice(1);
switchSection(Object.hasOwn(sections, initial) ? initial : 'direction');
const generated = $('.local-time');
generated.textContent = times.format(new Date(generated.dateTime));
publishControls();
