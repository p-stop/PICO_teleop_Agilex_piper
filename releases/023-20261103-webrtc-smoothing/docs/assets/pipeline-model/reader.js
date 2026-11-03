/* Pure teaching calculations + offline navigation; no device/network access. */
(function () {
  'use strict';
  function response(alpha, hz, duration = 1.2) {
    const points = [{t: 0, q: .4}];
    for (let k = 1; k <= Math.floor(duration * hz + 1e-9); k++) {
      points.push({t: k / hz, q: 1 - .6 * Math.pow(1 - alpha, k)});
    }
    return {points, tau: -1 / (hz * Math.log(1 - alpha)),
      reach95: Math.ceil(Math.log(.05) / Math.log(1 - alpha)) / hz};
  }
  function budgets(latency, lead, buffer, age) {
    return [
      {name: '首动作仍在未来：L < lead', slack: lead - latency, ok: latency < lead},
      {name: '请求未超时：L ≤ 300 ms', slack: 300 - latency, ok: latency <= 300},
      {name: '旧队列够用：B ≥ L + 40 ms', slack: buffer - latency - 40, ok: buffer >= latency + 40},
      {name: '观测未过旧：age + L ≤ 400 ms', slack: 400 - age - latency, ok: age + latency <= 400}
    ];
  }
  if (typeof module !== 'undefined') module.exports = {response, budgets};
  if (typeof document === 'undefined') return;
  const el = id => document.getElementById(id);
  const lessons = Array.from(document.querySelectorAll('.lesson'));
  let selected = 0;
  function showLesson(value) {
    selected = Math.max(0, Math.min(lessons.length - 1, Number(value)));
    lessons.forEach((node, i) => {node.hidden = i !== selected;});
    el('lesson-select').value = String(selected);
    el('lesson-progress').textContent = `${selected + 1} / ${lessons.length}`;
    el('previous').disabled = selected === 0;
    el('next').disabled = selected === lessons.length - 1;
  }
  document.querySelector('.lesson-controls').hidden = false;
  el('lesson-select').addEventListener('change', e => showLesson(e.target.value));
  el('previous').addEventListener('click', () => showLesson(selected - 1));
  el('next').addEventListener('click', () => showLesson(selected + 1));
  showLesson(0);
  // Keep all answers readable in print; restore the reader state afterwards.
  let openDetails = [];
  addEventListener('beforeprint', () => {
    openDetails = Array.from(document.querySelectorAll('details')).map(d => d.open);
    document.querySelectorAll('details').forEach(d => {d.open = true;});
  });
  addEventListener('afterprint', () => {
    document.querySelectorAll('details').forEach((d, i) => {d.open = openDetails[i];});
  });
  function plot() {
    const alpha = +el('ik-alpha').value, hz = +el('ik-hz').value;
    const result = response(alpha, hz), host = el('ik-chart');
    el('alpha-value').textContent = alpha.toFixed(2);
    el('hz-value').textContent = `${hz} Hz`;
    const width = Math.max(230, Math.floor(host.clientWidth));
    const height = 280, l = 60, r = 18, t = 30, b = 54;
    const X = x => l + x / 1.2 * (width - l - r), Y = y => t + (1.05 - y) / .7 * (height - t - b);
    let d = `M${X(0)},${Y(.4)}`;
    for (const p of result.points.slice(1)) d += `H${X(p.t)}V${Y(p.q)}`;
    d += `H${X(1.2)}`;
    const xticks = width < 450 ? [0,.4,.8,1.2] : [0,.2,.4,.6,.8,1,1.2];
    const grid = [.4,.6,.8,1].map(y => `<line class="grid" x1="${l}" x2="${width-r}" y1="${Y(y)}" y2="${Y(y)}"/><text x="${l-10}" y="${Y(y)+4}" text-anchor="end">${y.toFixed(1)}</text>`).join('');
    const labels = xticks.map(x => `<text x="${X(x)}" y="${height-b+20}" text-anchor="middle">${x.toFixed(1)}</text>`).join('');
    host.innerHTML = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${hz} Hz、α ${alpha} 下的标量 IK 阶梯响应，目标1 rad，时间常数${result.tau.toFixed(3)}秒">
      <rect x="${l}" y="${t}" width="${width-l-r}" height="${height-t-b}" class="grid"/>
      ${grid}${labels}<path class="target" d="M${X(0)},${Y(1)}H${X(1.2)}"/><path class="step" d="${d}"/>
      <text x="${l}" y="17">IK 目标 q（rad）</text><text x="${(l+width-r)/2}" y="${height-5}" text-anchor="middle">物理时间 t（s）</text>
      </svg>`;
    el('ik-status').textContent = `等效时间常数 ${result.tau.toFixed(3)} s；完成初始差值 95% 至少需要 ${result.reach95.toFixed(3)} s。虚线为恒定理想目标，实线为递推 IK 目标。`;
  }
  function updateBudget() {
    const ids = ['latency','lead','buffer','age'], values = ids.map(id => +el(id).value);
    ids.forEach((id, i) => {el(`${id}-value`).textContent = `${values[i]} ms`;});
    const rows = budgets(...values);
    el('budget-rows').innerHTML = rows.map(r => `<tr><td>${r.name}</td><td>${r.slack} ms</td><td class="${r.ok?'budget-pass':'budget-fail'}">${r.ok?'满足':'不满足'}</td></tr>`).join('');
    const failed = rows.filter(r => !r.ok);
    el('budget-status').textContent = failed.length ? `${failed.length} 项预算不满足。${failed.map(r=>r.name.split('：')[0]).join('；')}。` : '四个时间预算满足；仍需验证动作语义、接缝与真实跟踪。';
  }
  ['ik-alpha','ik-hz'].forEach(id => el(id).addEventListener('input', plot));
  ['latency','lead','buffer','age'].forEach(id => el(id).addEventListener('input', updateBudget));
  new ResizeObserver(plot).observe(el('ik-chart'));
  plot(); updateBudget();
})();
