/* Deterministic teaching models. No robot access, network requests or telemetry. */
(function () {
  'use strict';
  const TAU = 2 * Math.PI;
  const rms = a => Math.sqrt(a.reduce((s, x) => s + x * x, 0) / a.length);
  function aliasFrequency(f, fs) { return ((f + fs / 2) % fs + fs) % fs - fs / 2; }
  function linearAt(rows, t) {
    let lo = 0, hi = rows.length - 1;
    if (t <= rows[0][0]) return rows[0][1];
    if (t >= rows[hi][0]) return rows[hi][1];
    while (hi - lo > 1) { const m = (lo + hi) >> 1; if (rows[m][0] <= t) lo = m; else hi = m; }
    const a = rows[lo], b = rows[hi];
    return a[1] + (b[1] - a[1]) * (t - a[0]) / (b[0] - a[0]);
  }
  function bufferBudget(n, k, hz, latencyMs, marginMs) {
    const coverage = (n - k) / hz;
    return {coverage, slack: coverage - (latencyMs + marginMs) / 1000,
      prefix: Math.ceil(latencyMs * hz / 1000), span: (n - 1) / hz, total: n / hz};
  }
  function simulatePlant({inputHz = 30, controlHz = 60, recordHz = 30,
    delayMs = 70, bandwidthHz = 3, gapMs = 0}) {
    // A teaching plant, not an identified Piper model.
    // Exact first-order update over each 1 ms interval with held input.
    const dt = .001, duration = 4, decay = Math.exp(-TAU * bandwidthHz * dt);
    const desired = t => .45 * Math.sin(TAU * t) + .08 * Math.sin(TAU * 5 * t);
    let q = 0, u = 0, tick = 0;
    const truth = [], reference = [], commands = [];
    for (let i = 0; i <= duration / dt; i++) {
      const t = i * dt;
      if (i) q = decay * q + (1 - decay) * u;
      if (t + 1e-10 >= tick / controlHz) {
        const available = t - delayMs / 1000;
        u = available < 0 ? 0 : desired(Math.floor((available + 1e-10) * inputHz) / inputHz);
        commands.push([t, u]); tick++;
      }
      truth.push([t, q]); reference.push([t, desired(t)]);
    }
    const recorded = [];
    for (let i = 0; i <= duration * recordHz; i++) {
      const t = i / recordHz;
      if (gapMs && t >= 2 && t < 2 + gapMs / 1000) continue;
      recorded.push([t, truth[Math.min(truth.length - 1, Math.floor(t / dt + 1e-8))][1]]);
    }
    const reconstruction = truth.map(([t]) => [t, linearAt(recorded, t)]);
    return {truth, reference, commands, recorded, reconstruction,
      trackingRms: rms(truth.map((r, i) => r[1] - reference[i][1])),
      recordingRms: rms(truth.map((r, i) => r[1] - reconstruction[i][1])),
      maxGapMs: Math.max(...recorded.slice(1).map((r, i) => (r[0] - recorded[i][0]) * 1000))};
  }
  const api = {aliasFrequency, linearAt, bufferBudget, simulatePlant, rms};
  if (typeof module !== 'undefined') module.exports = api;
  if (typeof document === 'undefined') return;
  window.SignalMath = api;
  const $ = id => document.getElementById(id);
  const colors = ['#146c80', '#ba4b20', '#7058a3', '#65747e'];
  function linePath(rows, x, y, step) {
    return rows.map((r, i) => (i ? (step ? `H${x(r[0]).toFixed(2)}V` : 'L' + x(r[0]).toFixed(2) + ',') : 'M' + x(r[0]).toFixed(2) + ',') + y(r[1]).toFixed(2)).join('');
  }
  function chart(id, series, {xLabel = '时间 / s', yLabel = '关节位置 / rad', range = null} = {}) {
    const root = $(id), width = Math.max(290, root.clientWidth), height = 280;
    const left = 62, right = 18, top = 18, bottom = 48;
    const all = series.flatMap(s => s.rows), xs = all.map(r => r[0]), ys = all.map(r => r[1]);
    const xmin = range ? range[0] : Math.min(...xs), xmax = range ? range[1] : Math.max(...xs);
    const low = Math.min(...ys), high = Math.max(...ys), pad = Math.max(.005, (high - low) * .12);
    const ymin = low - pad, ymax = high + pad;
    const x = t => left + (width - left - right) * (t - xmin) / (xmax - xmin || 1);
    const y = v => top + (height - top - bottom) * (ymax - v) / (ymax - ymin);
    const ticks = width < 500 ? 3 : 5;
    let html = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${root.dataset.label || id}"><defs><clipPath id="${id}-clip"><rect x="${left}" y="${top}" width="${width-left-right}" height="${height-top-bottom}"/></clipPath></defs>`;
    for (let i = 0; i <= ticks; i++) {
      const t = xmin + (xmax - xmin) * i / ticks;
      html += `<path class="grid" d="M${x(t)},${top}V${height-bottom}"/><text x="${x(t)}" y="${height-bottom+20}" text-anchor="middle">${t.toFixed(2)}</text>`;
    }
    for (let i = 0; i <= 4; i++) {
      const v = ymin + (ymax - ymin) * i / 4;
      html += `<path class="grid" d="M${left},${y(v)}H${width-right}"/><text x="${left-10}" y="${y(v)+4}" text-anchor="end">${v.toFixed(2)}</text>`;
    }
    html += `<text x="${(left+width-right)/2}" y="${height-5}" text-anchor="middle">${xLabel}</text><text transform="translate(15 ${(top+height-bottom)/2}) rotate(-90)" text-anchor="middle">${yLabel}</text><g clip-path="url(#${id}-clip)">`;
    for (let i = 0; i < series.length; i++) {
      const s = series[i], color = s.color || colors[i];
      if (s.dots) html += s.rows.map(r => `<circle cx="${x(r[0])}" cy="${y(r[1])}" r="3" fill="${color}"/>`).join('');
      else html += `<path d="${linePath(s.rows,x,y,s.step)}" fill="none" stroke="${color}" stroke-width="${s.width||1.8}" ${s.dash?'stroke-dasharray="5 4"':''}/>`;
    }
    html += `</g><line class="hoverline" y1="${top}" y2="${height-bottom}" hidden/><rect class="hit" x="${left}" y="${top}" width="${width-left-right}" height="${height-top-bottom}" fill="transparent"/></svg>`;
    root.innerHTML = html + `<div class="legend">${series.map((s,i)=>`<span><i style="background:${s.color||colors[i]}"></i>${s.name}${s.dash?'（虚线）':''}${s.dots?'（点）':''}</span>`).join('')}</div><div class="plot-detail" aria-live="off">触摸或移动指针可读取最近记录点；连线仅用于显示。</div>`;
    const hit = root.querySelector('.hit'), svg = root.querySelector('svg');
    hit.addEventListener('pointermove', e => {
      const px = (e.clientX - svg.getBoundingClientRect().left) * width / svg.getBoundingClientRect().width;
      const t = Math.max(xmin, Math.min(xmax, xmin + (px-left)/(width-left-right)*(xmax-xmin)));
      const guide = root.querySelector('.hoverline'); guide.removeAttribute('hidden');guide.setAttribute('x1',x(t));guide.setAttribute('x2',x(t));
      root.querySelector('.plot-detail').textContent = `光标 ${t.toFixed(3)} s · ` + series.map(s => {
        const r = s.rows.reduce((a,b)=>Math.abs(a[0]-t)<Math.abs(b[0]-t)?a:b);
        return `${s.name} ${r[1].toFixed(4)} @ ${r[0].toFixed(3)} s`;
      }).join(' · ');
    });
  }
  function number(id) { return Number($(id).value); }
  function labels() { document.querySelectorAll('input[type=range]').forEach(e => {
    const out = document.querySelector(`output[for="${e.id}"]`); if(out)out.value=e.value;
  }); }
  function sampling() {
    const f=number('frequency'), fs=number('sample-rate'), method=$('interpolation').value, duration=1;
    const truth=Array.from({length:1201},(_,i)=>[i/1200,Math.sin(TAU*f*i/1200)]);
    const samples=Array.from({length:Math.floor(duration*fs)+1},(_,i)=>[i/fs,Math.sin(TAU*f*i/fs)]);
    const reconstructed=truth.map(([t])=>[t,method==='linear'?linearAt(samples,t):samples[Math.min(samples.length-1,Math.floor(t*fs+1e-9))][1]]);
    const alias=aliasFrequency(f,fs), aliased=Math.abs(f)>=fs/2;
    const series=[{name:'已知连续输入',rows:truth},{name:method==='linear'?'线性连接':'零阶保持',rows:reconstructed,step:method!=='linear'},{name:'采样点',rows:samples,dots:true}];
    if(aliased)series.push({name:`别名 ${alias.toFixed(1)} Hz`,rows:truth.map(([t])=>[t,Math.sin(TAU*alias*t)]),dash:true});
    chart('sampling-chart',series);
    $('sampling-status').textContent=aliased?`不满足严格 Nyquist 条件；有符号别名频率 ${alias.toFixed(1)} Hz。插值不能消除混叠。`:`满足此单一正弦的 Nyquist 条件；线性/ZOH 仍是近似，未使用理想 sinc。`;
  }
  function plant() {
    const r=simulatePlant({inputHz:number('hand-rate'),controlHz:number('control-rate'),recordHz:number('record-rate'),delayMs:number('delay'),bandwidthHz:number('bandwidth'),gapMs:number('gap')});
    chart('plant-chart',[{name:'期望轨迹',rows:r.reference},{name:'模拟实际运动',rows:r.truth},{name:'离散记录',rows:r.recorded,dots:true}]);
    chart('record-chart',[{name:'线性重建误差',rows:r.truth.map((v,i)=>[v[0],r.reconstruction[i][1]-v[1]])}],{yLabel:'重建 − 模拟真值 / rad'});
    $('plant-status').textContent=`跟踪 RMSE ${r.trackingRms.toFixed(4)} rad · 记录重建 RMSE ${r.recordingRms.toFixed(5)} rad · 最大记录间隔 ${r.maxGapMs.toFixed(1)} ms`;
  }
  function chunks() {
    const n=number('chunk-n');$('chunk-k').max=n-1;if(number('chunk-k')>=n)$('chunk-k').value=n-1;
    labels();
    const k=number('chunk-k'), hz=number('action-hz'), l=number('model-delay'), m=number('margin');
    const r=bufferBudget(n,k,hz,l,m), root=$('chunk-chart'), width=Math.max(290,root.clientWidth);
    const left=100,right=20, end=Math.max(r.total,k/hz+(l+m)/1000)*1.05;
    const x=t=>left+(width-left-right)*t/end, bar=(start,duration,y,color,label)=>`<rect x="${x(start)}" y="${y}" width="${Math.max(0,x(start+duration)-x(start))}" height="24" fill="${color}"/><text x="${left-10}" y="${y+17}" text-anchor="end">${label}</text>`;
    let svg=`<svg viewBox="0 0 ${width} 210" role="img" aria-label="动作覆盖与下一次推理延迟时间线">`;
    svg+=bar(0,r.total,28,colors[0],'旧 chunk')+bar(k/hz,l/1000,78,colors[1],'推理+传输')+bar(k/hz+l/1000,m/1000,128,colors[2],'调度裕量');
    for(let i=0;i<=n;i++)svg+=`<path stroke="#ffffff" opacity=".5" d="M${x(i/hz)},28v24"/>`;
    for(let i=0;i<=3;i++){const t=end*i/3;svg+=`<text x="${x(t)}" y="184" text-anchor="middle">${t.toFixed(2)}</text>`;}
    svg+=`<path class="hoverline" d="M${x(r.total)},20V160"/><text x="${(left+width-right)/2}" y="207" text-anchor="middle">物理时间 / s</text></svg>`;
    root.innerHTML=svg;
    $('chunk-status').textContent=`剩余覆盖 ${(r.coverage*1000).toFixed(1)} ms · 扣除延迟与裕量 ${r.slack>=0?'余量':'缺口'} ${Math.abs(r.slack*1000).toFixed(1)} ms · 延迟期间约 ${r.prefix} 步`;
    $('chunk-detail').textContent=`首末采样点跨度 ${r.span.toFixed(3)} s；含最后一步保持时覆盖 ${r.total.toFixed(3)} s。${r.slack<0?'当前预算无法连续供给动作。':'预算能覆盖本次确定延迟，仍不保证计划衔接或及时响应。'}此图不运行 RTC 生成器。`;
  }
  function real() {
    const evidence=window.SIGNAL_EVIDENCE, side=$('real-arm').value, j=number('real-joint');
    const s=evidence.series[side], stats=evidence.stats[side];
    chart('real-chart',[{name:'发布目标',rows:s.commands.map(r=>[r[0],r[j]]),step:true,dash:true},{name:'收到的反馈',rows:s.feedback.map(r=>[r[0],r[j]])}]);
    $('real-status').textContent=`第 ${j} 关节 · RMSE ${stats.rmse_rad[j-1].toFixed(5)} rad · 最大绝对误差 ${stats.max_abs_error_rad[j-1].toFixed(5)} rad · ${stats.error_samples} 个配对反馈点`;
  }
  const updates={sampling,plant,chunks,real};
  document.querySelectorAll('[data-update]').forEach(e=>e.addEventListener('input',()=>{labels();updates[e.dataset.update]();}));
  let scheduled;
  new ResizeObserver(()=>{cancelAnimationFrame(scheduled);scheduled=requestAnimationFrame(()=>Object.values(updates).forEach(f=>f()));}).observe($('experiments'));
  labels();Object.values(updates).forEach(f=>f());
})();
