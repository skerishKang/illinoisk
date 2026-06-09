// Strategy rendering for monday-strategy.html
function renderStrategyPage() {
  const data = STRATEGY_DATA;
  document.getElementById('stock-count').textContent = data.stocks.length;
  document.getElementById('strategy-meta').textContent = 
    `🕐 생성 ${data.generated_at.slice(0,16).replace('T',' ')} · ${data.market_update} · ${data.stocks.length}개 종목`;

  // Market section
  renderMarketSection(data.market);
  
  // ELO Ranking TOP 3
  renderEloRanking(data.stocks);
  
  // Stock list
  renderStrategyList(data.stocks);
}

function renderMarketSection(market) {
  document.getElementById('market-ultra').innerHTML = formatAnalysis(market.ultra_analysis);
  document.getElementById('market-deepseek').innerHTML = formatAnalysis(market.hermes_deepseek);
  document.getElementById('market-action-badge').textContent = market.ultra_action;
  document.getElementById('market-action-badge').className = 'badge badge-action ' + getActionClass(market.ultra_action);
  
  // Key indicators
  const indicators = document.getElementById('market-indicators');
  indicators.innerHTML = `
    <div class="indicator-row">
      <span class="indicator-label">울트라 액션</span>
      <span class="indicator-value ${getActionClass(market.ultra_action)}">${market.ultra_action}</span>
    </div>
  `;
}

function renderStrategyList(stocks) {
  const container = document.getElementById('strategy-list');
  
  stocks.forEach((stock, idx) => {
    const card = document.createElement('div');
    card.className = 'strategy-card';
    card.setAttribute('data-name', stock.name);
    card.setAttribute('data-ticker', stock.ticker);
    card.setAttribute('data-action', stock.ultra.action);
    card.setAttribute('data-agreement', stock.hermes_deepseek.agreement);
    card.setAttribute('data-category', stock.category);
    
    const changeClass = stock.change >= 0 ? 'positive' : 'negative';
    const changeArrow = stock.change >= 0 ? '🟢' : '🔴';
    
    card.innerHTML = `
      <div class="strategy-header">
        <div class="stock-title">
          <h3>${stock.name} <span class="tag">${stock.category}</span></h3>
          <span class="ticker-code">${stock.ticker}</span>
        </div>
        <div class="stock-meta">
          <span class="price">${stock.price.toLocaleString()}원</span>
          <span class="change ${changeClass}">${changeArrow} ${stock.change >= 0 ? '+' : ''}${stock.change.toFixed(2)}%</span>
        </div>
      </div>
      
      <div class="strategy-stats">
        <div class="stat-item ${stock.rsi <= 30 ? 'oversold' : stock.rsi >= 70 ? 'overbought' : ''}">
          <span class="stat-lbl">RSI</span>
          <span class="stat-val">${stock.rsi.toFixed(1)}</span>
        </div>
        <div class="stat-item">
          <span class="stat-lbl">지지</span>
          <span class="stat-val">${stock.support_1.toLocaleString()}</span>
        </div>
        <div class="stat-item">
          <span class="stat-lbl">저항</span>
          <span class="stat-val">${stock.resistance_1.toLocaleString()}</span>
        </div>
        <div class="stat-item">
          <span class="stat-lbl">거래량</span>
          <span class="stat-val ${stock.volume_ratio >= 2 ? 'high' : ''}">${stock.volume_ratio.toFixed(1)}x</span>
        </div>
      </div>

      <div class="strategy-comparison">
        <div class="analysis-card ultra-card">
          <div class="card-header">
            <span class="badge badge-ultra">🟦 울트라</span>
            <span class="agent-badge agent-${stock.ultra.elo ? stock.ultra.elo.agent_style : 'tech'}">${getAgentStyleIcon(stock.ultra.elo ? stock.ultra.elo.agent_style : 'tech')} ${stock.ultra.elo ? stock.ultra.elo.agent_label : '테크니컬'}</span>
            <span class="badge badge-action ${getActionClass(stock.ultra.action)}">${stock.ultra.action}</span>
            <span class="badge badge-elo ${getEloColorClass(stock.ultra.elo ? stock.ultra.elo.score : 1200)}">${getEloIcon(stock.ultra.elo ? stock.ultra.elo.score : 1200)} ELO ${stock.ultra.elo ? stock.ultra.elo.score : 1200}</span>
          </div>
          <div class="card-body">
            ${formatAnalysis(stock.ultra.analysis)}
            <div class="action-details">
              <div class="detail-row"><span class="lbl">진입:</span><span class="val">${stock.ultra.entry || '—'}</span></div>
              <div class="detail-row"><span class="lbl">목표:</span><span class="val">${stock.ultra.target || '—'}</span></div>
              <div class="detail-row"><span class="lbl">손절:</span><span class="val" style="color: var(--up)">${stock.ultra.stop || '—'}</span></div>
            </div>
            <details class="reasoning-toggle">
              <summary>근거 보기</summary>
              <p class="reasoning-text">${stock.ultra.reasoning}</p>
            </details>
          </div>
        </div>
        
        <div class="analysis-card deepseek-card">
          <div class="card-header">
            <span class="badge badge-deepseek">🟩 Hermes 딥시크</span>
            <span class="badge badge-agreement ${getAgreementClass(stock.hermes_deepseek.agreement)}">${stock.hermes_deepseek.agreement}</span>
          </div>
          <div class="card-body">
            ${formatAnalysis(stock.hermes_deepseek.analysis)}
            <div class="risk-warning">
              <span class="risk-label">⚠️ 리스크:</span>
              <span>${stock.hermes_deepseek.risk}</span>
            </div>
            <div class="supplement-note">
              <span class="supplement-label">📎 보충:</span>
              <span>${stock.hermes_deepseek.supplement}</span>
            </div>
          </div>
        </div>
      </div>
    `;
    
    container.appendChild(card);
  });
}

function renderEloRanking(stocks) {
  // Sort by ELO score descending, filter out stocks with 0 total trades (unranked)
  const ranked = [...stocks]
    .filter(s => s.ultra && s.ultra.elo && s.ultra.elo.total > 0)
    .sort((a, b) => (b.ultra.elo.score || 1200) - (a.ultra.elo.score || 1200))
    .slice(0, 3);
  
  // If no ranked stocks yet, show top 3 by default ELO (all 1200)
  if (ranked.length === 0) {
    const container = document.getElementById('elo-ranking');
    if (container) {
      container.innerHTML = `
        <div class="elo-ranking-empty">
          <p>아직 ELO 평가가 완료되지 않았습니다 — Phase 1b 트레이딩 토너먼트 시작 후 순위가 생성됩니다</p>
        </div>
      `;
    }
    return;
  }
  
  const container = document.getElementById('elo-ranking');
  if (!container) return;
  
  const medals = ['🥇', '🥈', '🥉'];
  let html = '<div class="elo-ranking-grid">';
  
  ranked.forEach((stock, idx) => {
    const elo = stock.ultra.elo;
    const eloColor = getEloColorClass(elo.score);
    const accDisplay = elo.accuracy !== '--' ? elo.accuracy : '—';
    
    html += `
      <div class="elo-ranking-card ${idx === 0 ? 'elo-rank-first' : ''}">
        <div class="elo-rank-medal">${medals[idx] || ''}</div>
        <div class="elo-rank-name">${stock.name}</div>
        <div class="elo-rank-agent ${getAgentStyleBadgeClass(elo.agent_style)}">${getAgentStyleIcon(elo.agent_style)} ${elo.agent_label}</div>
        <div class="elo-rank-score ${eloColor}">ELO ${elo.score}</div>
        <div class="elo-rank-stats">
          <span>${elo.wins}승 ${elo.losses}패</span>
          <span>정확도 ${accDisplay}${accDisplay !== '—' ? '%' : ''}</span>
        </div>
      </div>
    `;
  });
  
  html += '</div>';
  container.innerHTML = html;
}

function getEloColorClass(score) {
  if (score >= 1400) return 'elo-high';
  if (score >= 1200) return 'elo-mid';
  return 'elo-low';
}

function getEloIcon(score) {
  if (score >= 1400) return '🟢';
  if (score >= 1200) return '🟡';
  if (score < 1200 && score > 0) return '🔴';
  return '⚪';
}

function getAgentStyleIcon(style) {
  const icons = { 'tech': '🟦', 'fund': '🟩', 'supply': '🟨' };
  return icons[style] || '⚪';
}

function getAgentStyleBadgeClass(style) {
  return 'agent-' + (style || 'tech');
}

function handleSearch() {
  const query = document.getElementById('search-input').value.toLowerCase();
  const action = document.getElementById('action-filter').value;
  const agreement = document.getElementById('agreement-filter').value;
  
  const cards = document.querySelectorAll('.strategy-card');
  cards.forEach(card => {
    const name = card.getAttribute('data-name').toLowerCase();
    const ticker = card.getAttribute('data-ticker');
    const cardAction = card.getAttribute('data-action');
    const cardAgreement = card.getAttribute('data-agreement');
    
    const matchQuery = !query || name.includes(query) || ticker.includes(query);
    const matchAction = !action || cardAction === action;
    const matchAgreement = !agreement || cardAgreement === agreement;
    
    card.style.display = (matchQuery && matchAction && matchAgreement) ? '' : 'none';
  });
}

function formatAnalysis(text) {
  if (!text || text.trim() === '') return '<p class="analysis-line" style="color:var(--text2);opacity:0.5">분석 내용이 비어있습니다 — Phase 2 Ultra 파이프라인 구축 필요</p>';
  
  // Strip markdown formatting
  text = text
    .replace(/\*\*(.*?)\*\*/g, '$1')       // **bold** → text
    .replace(/__(.*?)__/g, '$1')            // __bold__ → text
    .replace(/\*(.*?)\*/g, '$1')            // *italic* → text
    .replace(/_(.*?)_/g, '$1')              // _italic_ → text
    .replace(/~~(.*?)~~/g, '$1')            // ~~strikethrough~~ → text
    .replace(/`{1,3}[^`]*`{1,3}/g, '')      // `code` → empty
    .replace(/^#{1,6}\s+/gm, '')            // ## headers → text
    .replace(/^>\s+/gm, '')                 // > blockquote prefix
    .replace(/\[([^\]]*)\]\([^)]*\)/g, '$1') // [text](url) → text
    .trim();
  
  return text.split('\n').filter(l => l.trim()).map(line => {
    line = line.trim();
    if (line.startsWith('💡') || line.startsWith('🔴') || line.startsWith('🟡') || line.startsWith('✅')) {
      return `<p class="analysis-line highlight">${line}</p>`;
    }
    if (line.match(/^\d+[️⃣.]/)) {
      return `<p class="analysis-line num-item">${line}</p>`;
    }
    return `<p class="analysis-line">${line}</p>`;
  }).join('');
}

function getActionClass(action) {
  const map = {
    '딥바잉': 'action-deepbuy',
    '분할매수': 'action-buy',
    '관망 (일부 분할매수 검토)': 'action-watch',
    '관망 (일부 익절 검토)': 'action-watch',
    '관망 (바닥 확인 후)': 'action-watch',
    '관망 (바닥권 분할매수)': 'action-watch',
    '관망 (딥바잉 주시)': 'action-watch',
    '관망 (조정 시 분할매수)': 'action-watch',
    '관망 (진입 비권장)': 'action-watch',
    '관망 (과매도 구간 주시)': 'action-watch',
    '관망': 'action-watch',
    '익절': 'action-sell',
    '일부 익절 / 관망': 'action-sell',
    '홀딩': 'action-hold'
  };
  // Find match
  for (const [key, val] of Object.entries(map)) {
    if (action.startsWith(key)) return val;
  }
  return 'action-watch';
}

function getAgreementClass(agreement) {
  const map = {
    '동의': 'agree-yes',
    '부분 동의': 'agree-partial',
    '반박': 'agree-no'
  };
  return map[agreement] || 'agree-partial';
}
