// Theme toggle
function initTheme() {
  const saved = localStorage.getItem('theme');
  if (saved === 'light') {
    document.documentElement.setAttribute('data-theme', 'light');
    const btn = document.getElementById('themeBtn');
    if (btn) btn.textContent = '☀️';
  }
}

function toggleTheme() {
  const html = document.documentElement;
  const isDark = html.getAttribute('data-theme') !== 'light';
  if (isDark) {
    html.setAttribute('data-theme', 'light');
    localStorage.setItem('theme', 'light');
    document.getElementById('themeBtn').textContent = '☀️';
  } else {
    html.removeAttribute('data-theme');
    localStorage.setItem('theme', 'dark');
    document.getElementById('themeBtn').textContent = '🌙';
  }
}

// Parse number from 억/원 string
function parseValue(val) {
  if (!val || val === '—' || val === 'N/A' || val.trim() === '') return null;
  const numStr = val.replace(/[,억원\s]/g, '');
  const num = parseFloat(numStr);
  if (isNaN(num)) return null;
  if (val.includes('억')) return num * 100000000;
  if (val.includes('만')) return num * 10000;
  return num;
}

function isNegative(val) {
  if (!val || val === '—') return false;
  return val.startsWith('-');
}

// Build stats row - REMOVED per user request
function buildStats(stocks) {
  // No-op: stats cards removed
}

// Create stock table row
function createStockRow(stock, showLink = true) {
  const tr = document.createElement('tr');
  if (showLink) {
    tr.style.cursor = 'pointer';
    tr.addEventListener('click', () => {
      window.location.href = `stock.html?name=${encodeURIComponent(stock.name)}`;
    });
  }

  function cell(val, cls = '') {
    const missing = !val || val === '—' || val.trim() === '';
    const neg = isNegative(val);
    return `<td class="num${cls ? ' '+cls : ''}${neg ? ' negative' : ''}${missing ? ' missing' : ''}">${missing ? '—' : val}</td>`;
  }

  tr.innerHTML = `
    <td class="name-cell"><span>${stock.name}</span> <span class="tag">${stock.category}</span></td>
    ${cell(stock.revenue)}
    ${cell(stock.op_profit)}
    ${cell(stock.net_income)}
    ${cell(stock.eps)}
    ${cell(stock.assets)}
    ${cell(stock.equity)}
    ${cell(stock.cash)}
  `;
  return tr;
}

// Build table
function buildTable(data, containerId, sortField = 'revenue', sortDir = -1) {
  const container = document.getElementById(containerId);
  if (!container) return;

  const sorted = [...data].sort((a, b) => {
    if (sortField === 'name') {
      return a.name.localeCompare(b.name) * sortDir;
    }
    const va = parseValue(a[sortField]) || 0;
    const vb = parseValue(b[sortField]) || 0;
    return (va - vb) * sortDir;
  });

  const fields = [
    { key: 'name', label: '종목명' },
    { key: 'revenue', label: '매출액' },
    { key: 'op_profit', label: '영업이익' },
    { key: 'net_income', label: '순이익' },
    { key: 'eps', label: 'EPS' },
    { key: 'assets', label: '자산총계' },
    { key: 'equity', label: '자본총계' },
    { key: 'cash', label: '현금성자산' }
  ];

  const table = document.createElement('table');
  const thead = document.createElement('thead');
  thead.innerHTML = '<tr>' + fields.map(f =>
    `<th onclick="sortTable('${containerId}', '${f.key}')" data-field="${f.key}">
      ${f.label} <span class="sort-icon">${f.key === sortField ? (sortDir === -1 ? '▼' : '▲') : '↕'}</span>
    </th>`
  ).join('') + '</tr>';
  table.appendChild(thead);

  const tbody = document.createElement('tbody');
  sorted.forEach(s => tbody.appendChild(createStockRow(s)));
  table.appendChild(tbody);

  container.innerHTML = '';
  const wrap = document.createElement('div');
  wrap.className = 'table-wrap';
  wrap.appendChild(table);
  container.appendChild(wrap);

  window.currentSort = { field: sortField, dir: sortDir };
  window.currentData = data;
  window.containerId = containerId;
}

function sortTable(containerId, field) {
  if (!window.currentSort) return;
  const data = window.currentData || STOCKS;
  const dir = (field === window.currentSort.field) ? -window.currentSort.dir : -1;
  window.currentSort = { field, dir };
  buildTable(data, containerId, field, dir);
}

// Search filter
function filterTable(query, category = '') {
  let filtered = STOCKS;
  if (query) {
    const q = query.toLowerCase();
    filtered = filtered.filter(s =>
      s.name.toLowerCase().includes(q) ||
      s.ticker.includes(q) ||
      s.category.toLowerCase().includes(q)
    );
  }
  if (category) {
    filtered = filtered.filter(s => s.category === category);
  }
  buildTable(filtered, 'stock-table');
}

// Get URL param
function getParam(name) {
  const params = new URLSearchParams(window.location.search);
  return params.get(name);
}

initTheme();
