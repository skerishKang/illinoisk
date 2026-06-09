// D3.js Value Chain Visualization
function renderValueChain() {
  const svg = d3.select('#valuechain-svg');
  if (svg.empty()) return;
  
  const width = svg.node().clientWidth || 960;
  const height = 600;
  
  svg.attr('viewBox', `0 0 ${width} ${height}`);
  
  // Define nodes (companies grouped by value chain stage)
  const nodes = [
    // Equipment
    { id: '장비', label: '장비사', x: width * 0.15, y: 60, type: 'group' },
    { id: '유진테크', label: '유진테크', x: width * 0.15, y: 150, type: 'company', group: '장비' },
    { id: '주성엔지니어링', label: '주성엔지니어링', x: width * 0.15, y: 230, type: 'company', group: '장비' },
    { id: '케이씨텍', label: '케이씨텍', x: width * 0.15, y: 310, type: 'company', group: '장비' },
    { id: '원익IPS', label: '원익IPS', x: width * 0.15, y: 390, type: 'company', group: '장비' },
    { id: 'HPSP', label: 'HPSP', x: width * 0.15, y: 470, type: 'company', group: '장비' },
    { id: '에스에프에이', label: '에스에프에이', x: width * 0.15, y: 550, type: 'company', group: '장비' },
    
    // Materials
    { id: '소재', label: '소재/부품', x: width * 0.35, y: 60, type: 'group' },
    { id: '동진쎄미켐', label: '동진쎄미켐', x: width * 0.35, y: 150, type: 'company', group: '소재' },
    { id: '솔브레인', label: '솔브레인', x: width * 0.35, y: 230, type: 'company', group: '소재' },
    { id: '이엔에프', label: '이엔에프테크', x: width * 0.35, y: 310, type: 'company', group: '소재' },
    { id: 'ISC', label: 'ISC', x: width * 0.35, y: 390, type: 'company', group: '소재' },
    { id: '리노공업', label: '리노공업', x: width * 0.35, y: 470, type: 'company', group: '소재' },
    { id: '에스앤에스텍', label: '에스앤에스텍', x: width * 0.35, y: 550, type: 'company', group: '소재' },
    
    // Fabs (Customers)
    { id: '고객사', label: '고객사(Fab)', x: width * 0.55, y: 60, type: 'group' },
    { id: '삼성전자', label: '삼성전자', x: width * 0.55, y: 180, type: 'customer', group: '고객사' },
    { id: 'SK하이닉스', label: 'SK하이닉스', x: width * 0.55, y: 280, type: 'customer', group: '고객사' },
    { id: 'DB하이텍', label: 'DB하이텍', x: width * 0.55, y: 380, type: 'company', group: '고객사' },
    { id: '제주반도체', label: '제주반도체', x: width * 0.55, y: 480, type: 'company', group: '고객사' },
    
    // OSAT/PCB
    { id: '후공정', label: '후공정/PCB', x: width * 0.75, y: 60, type: 'group' },
    { id: '하나마이크론', label: '하나마이크론', x: width * 0.75, y: 150, type: 'company', group: '후공정' },
    { id: '두산테스나', label: '두산테스나', x: width * 0.75, y: 230, type: 'company', group: '후공정' },
    { id: 'SFA반도체', label: 'SFA반도체', x: width * 0.75, y: 310, type: 'company', group: '후공정' },
    { id: '심텍', label: '심텍', x: width * 0.75, y: 390, type: 'company', group: '후공정' },
    { id: '대덕전자', label: '대덕전자', x: width * 0.75, y: 470, type: 'company', group: '후공정' },
    { id: '이수페타시스', label: '이수페타시스', x: width * 0.75, y: 550, type: 'company', group: '후공정' },
    
    // Test
    { id: '테스트', label: '검사/테스트', x: width * 0.9, y: 300, type: 'group' },
    { id: 'GST', label: 'GST', x: width * 0.9, y: 400, type: 'company', group: '테스트' },
    { id: '고영', label: '고영', x: width * 0.9, y: 500, type: 'company', group: '테스트' },
  ];
  
  // Links: equipment -> fab -> OSAT -> test
  const links = [
    // Equipment to Fabs
    { source: '유진테크', target: '삼성전자' },
    { source: '유진테크', target: 'SK하이닉스' },
    { source: '주성엔지니어링', target: '삼성전자' },
    { source: '주성엔지니어링', target: 'SK하이닉스' },
    { source: '케이씨텍', target: '삼성전자' },
    { source: '케이씨텍', target: 'SK하이닉스' },
    { source: '원익IPS', target: '삼성전자' },
    { source: '원익IPS', target: 'SK하이닉스' },
    { source: 'HPSP', target: '삼성전자' },
    { source: 'HPSP', target: 'SK하이닉스' },
    { source: '에스에프에이', target: '삼성전자' },
    { source: '에스에프에이', target: 'SK하이닉스' },
    
    // Materials to Fabs
    { source: '동진쎄미켐', target: '삼성전자' },
    { source: '동진쎄미켐', target: 'SK하이닉스' },
    { source: '솔브레인', target: '삼성전자' },
    { source: '솔브레인', target: 'SK하이닉스' },
    { source: '이엔에프', target: '삼성전자' },
    { source: '이엔에프', target: 'SK하이닉스' },
    { source: 'ISC', target: '삼성전자' },
    { source: 'ISC', target: 'SK하이닉스' },
    { source: '리노공업', target: 'SK하이닉스' },
    { source: '에스앤에스텍', target: '삼성전자' },
    { source: '에스앤에스텍', target: 'SK하이닉스' },
    
    // Fabs to OSAT/PCB
    { source: '삼성전자', target: '하나마이크론' },
    { source: 'SK하이닉스', target: '하나마이크론' },
    { source: '삼성전자', target: '두산테스나' },
    { source: 'SK하이닉스', target: '두산테스나' },
    { source: '삼성전자', target: 'SFA반도체' },
    { source: 'SK하이닉스', target: 'SFA반도체' },
    { source: '삼성전자', target: '심텍' },
    { source: 'SK하이닉스', target: '심텍' },
    { source: 'DB하이텍', target: '하나마이크론' },
    { source: 'DB하이텍', target: 'SFA반도체' },
    
    // PCB to Test
    { source: '심텍', target: 'GST' },
    { source: '대덕전자', target: 'GST' },
    { source: '하나마이크론', target: 'GST' },
    { source: '하나마이크론', target: '고영' },
    { source: 'SFA반도체', target: '고영' },
  ];
  
  const nodeMap = {};
  nodes.forEach(n => nodeMap[n.id] = n);
  
  // Draw links
  svg.selectAll('.link')
    .data(links.map(l => ({ source: nodeMap[l.source], target: nodeMap[l.target] })).filter(l => l.source && l.target))
    .enter()
    .append('line')
    .attr('class', 'link')
    .attr('x1', d => d.source.x)
    .attr('y1', d => d.source.y)
    .attr('x2', d => d.target.x)
    .attr('y2', d => d.target.y);
  
  // Draw nodes
  const nodeGroup = svg.selectAll('.node')
    .data(nodes)
    .enter()
    .append('g')
    .attr('class', 'node')
    .attr('transform', d => `translate(${d.x},${d.y})`);
  
  nodeGroup.append('circle')
    .attr('r', d => d.type === 'group' ? 8 : 6)
    .attr('fill', d => {
      if (d.type === 'group') return 'none';
      if (d.type === 'customer') return '#f39c12';
      return '#2d6bff';
    })
    .attr('stroke', d => {
      if (d.type === 'group') return '#aaa';
      return 'none';
    })
    .attr('stroke-width', d => d.type === 'group' ? 2 : 0)
    .on('click', (event, d) => {
      if (d.type === 'group' || d.type === 'customer') return;
      window.open(`stock.html?name=${encodeURIComponent(d.id)}`, '_blank');
    });
  
  nodeGroup.append('text')
    .attr('dx', d => d.type === 'group' ? -80 : 10)
    .attr('dy', 4)
    .attr('font-size', d => d.type === 'group' ? 14 : 11)
    .attr('font-weight', d => d.type === 'group' ? 'bold' : 'normal')
    .attr('fill', d => {
      if (d.type === 'customer') return '#f39c12';
      return null;
    })
    .text(d => d.label);
}

// Render chart on load
document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('valuechain-svg')) {
    renderValueChain();
  }
});
