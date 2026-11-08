(() => {
  'use strict';
  const get = id => document.getElementById(id);
  const data = JSON.parse(get('data').textContent);
  const {panel, protocol, benchmark} = data;
  const words = {
    fa: {
      navLab: 'آزمایش', navStudy: 'نتایج پژوهش', kicker: 'آزمایشگاه تعاملی یادگیری',
      hero: 'وقتی جای پاداش عوض می‌شود',
      intro: 'دو بو را انتخاب کنید و ببینید مدلِ مدار بویایی مگس پس از جابه‌جایی پاداش چگونه انتخابش را تغییر می‌دهد.',
      odorCount: 'بوی اندازه‌گیری‌شده', edgeCount: 'اتصال عصبی ثبت‌شده', step1: '۰۱ / تجربه کنید',
      labTitle: 'آزمایش خودتان را اجرا کنید', labIntro: 'بوها را عوض کنید و منحنی یادگیری را برای همان جفت ببینید.',
      browser: 'اجرای محلی در مرورگر', odorA: 'بوی اول', odorB: 'بوی دوم', firstTarget: 'پاداش اول در نمونه',
      seed: 'بذر تصادفی', run: 'اجرای شبیه‌سازی', download: 'دریافت نتیجه (JSON)',
      runNote: 'هر دو ترتیب پاداش به‌طور برابر در منحنی‌ها لحاظ می‌شوند. این گزینه ترتیب نمونهٔ زیر را تعیین می‌کند.',
      error: 'دو بوی متفاوت انتخاب کنید و بذر را به‌صورت عدد صحیح معتبر وارد کنید.', early: 'درصد درست در ۲۰ تلاش اول پس از تغییر',
      runStatus: n => `${n} اجرای شبیه‌سازی برای هر حالت`, observed: 'مدار ثبت‌شده', rewired: 'میانگین بازسیم‌کشی',
      direct: 'ورودی مستقیم گیرنده‌ها', chance: 'بدون یادگیری', jump: 'برو به تغییر پاداش', trial: 'تلاش',
      trialLabel: (n, total, after) => `تلاش ${n} از ${total} · ${after ? 'بعد از تغییر' : 'قبل از تغییر'}`,
      target: 'بوی پاداش‌دار', choice: 'انتخاب مدل', reward: 'پاداش گرفت', miss: 'پاداش نگرفت', control1: 'مدار بازسیم‌کشی‌شدهٔ اول',
      sampleNote: 'دو کارت یک اجرای نمونه با شرایط تصادفی مشترک را نشان می‌دهند.',
      step2: '۰۲ / نتیجهٔ پژوهش', studyTitle: 'مقایسه روی همهٔ جفت‌های بو',
      studyCount: (pairs, episodes, controls) => `${pairs} جفت بو · ${episodes} اجرای شبیه‌سازی برای هر حالت · ${controls} مدار کنترل`,
      saved: 'آزمون مرجع ثبت‌شده', finding: 'در این پروتکل، آرایش واقعی مدار مزیتی نشان نداد.',
      controlRange: (low, high) => `نتیجهٔ مدار واقعی در محدودهٔ مدارهای کنترل بود (${low} تا ${high}).`,
      scope: 'نتیجه مربوط به مدلِ یک نمونهٔ کالبدی است. برای تعمیم به رفتار مگس زنده به آزمون رفتاری مستقل نیاز است.',
      condition: 'حالت', before: '۲۰ تلاش آخر قبل از تغییر', late: '۲۰ تلاش آخر بعد از تغییر',
      switchAt: n => `تغییر پاداش در تلاش ${n}`, plotLabel: 'درصد انتخاب درست در هر تلاش برای سه حالت مدل',
      methods: 'روش، تنظیمات و منابع', methodBody: 'اتصال‌ها از جدول مدار بویایی FAFB و پاسخ بوها از DoOR 2.0 آمده‌اند. پاسخ گیرنده نمایندهٔ ورودی به مدار است. فقط موارد دارای اندازه‌گیری کامل وارد شدند. بازسیم‌کشی تعداد اتصال‌های هر نورون را حفظ می‌کند. انتخاب‌ها و پاداش‌ها خروجی شبیه‌سازی‌اند.',
      settings: (channels, neurons, cells, lr, exploration, cutoff) => `${channels} کانال بویایی، ${neurons} نورون رابط، ${cells} سلول کنیون. نرخ یادگیری ${lr}، احتمال کاوش ${exploration} و سهم هدف سلول‌های فعال ${cutoff}.`,
      sourceNames: ['جدول اتصالات و مقالهٔ FAFB', 'مستندات پاسخ‌های بویایی DoOR 2.0'],
      footer: 'FlyFlip Lab · آزمایش پژوهشی قابل اجرا در مرورگر · اتصالات و پاسخ‌های منتشرشده، تصمیم‌ها و پاداش‌های شبیه‌سازی‌شده',
    },
    en: {
      navLab: 'Experiment', navStudy: 'Study results', kicker: 'Interactive learning lab',
      hero: 'When the reward moves',
      intro: 'Choose two measured odors. See how a fruit-fly circuit model changes its choices when the reward moves to the other odor.',
      odorCount: 'measured odors', edgeCount: 'observed connections', step1: '01 / Run it yourself',
      labTitle: 'Run your own experiment', labIntro: 'Change the odors and inspect the learning curve for that pair.',
      browser: 'Runs in this browser', odorA: 'First odor', odorB: 'Second odor', firstTarget: 'Sample starts with',
      seed: 'Random seed', run: 'Run simulation', download: 'Download result (JSON)',
      runNote: 'Curves balance both reward orders. This setting picks the order for the sample below.',
      error: 'Choose two different odors and enter a valid whole-number seed.', early: 'Correct in the first 20 trials after the switch',
      runStatus: n => `${n} simulated episodes per condition`, observed: 'Observed wiring', rewired: 'Rewired mean',
      direct: 'Direct receptors', chance: 'No learning', jump: 'Jump to reward switch', trial: 'Trial',
      trialLabel: (n, total, after) => `Trial ${n} of ${total} · ${after ? 'After switch' : 'Before switch'}`,
      target: 'Rewarded odor', choice: 'Model choice', reward: 'Reward received', miss: 'No reward', control1: 'First rewired control',
      sampleNote: 'The two cards show one paired episode under the same random actions.',
      step2: '02 / Read the study', studyTitle: 'Comparison across all odor pairs',
      studyCount: (pairs, episodes, controls) => `${pairs} odor pairs · ${episodes} simulated episodes per condition · ${controls} rewired controls`,
      saved: 'Recorded benchmark', finding: 'Observed wiring showed no advantage under this protocol.',
      controlRange: (low, high) => `Its early accuracy fell within the control range (${low} to ${high}).`,
      scope: 'The model uses one anatomical specimen. Independent behavioral measurements are needed to evaluate how well it describes live flies.',
      condition: 'Condition', before: 'Last 20 before switch', late: 'Last 20 after switch',
      switchAt: n => `Reward switches at trial ${n}`, plotLabel: 'Percentage of correct choices by trial for three model conditions',
      methods: 'Methods, settings and sources', methodBody: 'The FAFB circuit table supplies edges and DoOR 2.0 supplies measured odor responses. Receptor responses serve as a proxy for circuit input. The panel uses complete measurements. Rewiring preserves each neuron’s connection count. Choices and rewards are simulation outputs.',
      settings: (channels, neurons, cells, lr, exploration, cutoff) => `${channels} odor channels, ${neurons} projection neurons, ${cells} Kenyon cells. Learning rate ${lr}, exploration probability ${exploration}, target active fraction ${cutoff}.`,
      sourceNames: ['FAFB connectivity table and paper', 'DoOR 2.0 response matrix documentation'],
      footer: 'FlyFlip Lab · A browser experiment with published connections, measured responses and simulated choices',
    },
  };

  const series = ['observed', 'rewired', 'direct'];
  const benchmarkCurves = Object.fromEntries(series.map(key => [key, benchmark[key].trial_accuracy]));
  const colors = {observed: 'var(--obs)', rewired: 'var(--ctrl)', direct: 'var(--direct)', chance: 'var(--muted)'};
  const switchTrial = protocol.phase_trials + 1;
  const odors = panel.odors.map(item => item.name);
  let language = 'fa';
  let result;
  const t = key => words[language][key];
  const number = value => new Intl.NumberFormat(language === 'fa' ? 'fa-IR' : 'en-US').format(value);
  const percent = value => new Intl.NumberFormat(language === 'fa' ? 'fa-IR' : 'en-US', {
    style: 'percent', minimumFractionDigits: 2, maximumFractionDigits: 2,
  }).format(value);

  function element(tag, text, className) {
    const node = document.createElement(tag);
    node.textContent = text;
    if (className) node.className = className;
    return node;
  }

  function svg(plot, name, attrs, text) {
    const node = document.createElementNS('http://www.w3.org/2000/svg', name);
    for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
    if (text) node.textContent = text;
    plot.append(node);
    return node;
  }

  function drawPlot(id, curves, trial) {
    const plot = get(id);
    const last = curves.observed.length;
    const width = Math.max(260, Math.min(660, plot.clientWidth || 660));
    const right = width - 18;
    const x = i => 46 + (i - 1) * (right - 46) / (last - 1);
    const y = v => 143 - v * 117;
    const label = {fill:'#546459', 'font-size':12};
    plot.replaceChildren();
    plot.setAttribute('viewBox', `0 0 ${width} 169`);
    plot.setAttribute('aria-label', t('plotLabel'));
    svg(plot, 'title', {}, t('plotLabel'));
    for (const value of [0, .5, 1]) {
      svg(plot, 'line', {x1:46,x2:right,y1:y(value),y2:y(value),stroke:'#d1d9cd','stroke-dasharray':value === .5 ? '4 4' : 'none'});
      svg(plot, 'text', {x:40,y:y(value) + 4,'text-anchor':'end',...label}, `${number(value * 100)}%`);
    }
    svg(plot, 'line', {x1:x(switchTrial),x2:x(switchTrial),y1:23,y2:143,stroke:'#875830','stroke-dasharray':'4 4'});
    svg(plot, 'text', {x:x(switchTrial),y:15,'text-anchor':'middle',...label,fill:'#7c482c'}, t('switchAt')(number(switchTrial)));
    for (const key of ['direct', 'observed', 'rewired']) {
      svg(plot, 'polyline', {points:curves[key].map((v, i) => `${x(i + 1)},${y(v)}`).join(' '),
        fill:'none',stroke:colors[key],'stroke-width':key === 'rewired' ? 1.8 : 2.4,'stroke-linejoin':'round',
        'stroke-dasharray':key === 'rewired' ? '5 3' : 'none'});
    }
    if (trial) {
      svg(plot, 'line', {x1:x(trial),x2:x(trial),y1:26,y2:143,stroke:'#68776a',opacity:.65});
      for (const key of series) svg(plot, 'circle', {cx:x(trial),cy:y(curves[key][trial - 1]),r:3.7,fill:colors[key],stroke:'#fffdf6'});
    }
    svg(plot, 'text', {x:46,y:162,...label}, `${t('trial')} ${number(1)}`);
    svg(plot, 'text', {x:right,y:162,'text-anchor':'end',...label}, `${t('trial')} ${number(last)}`);
  }

  function renderMetrics(id, values) {
    get(id).replaceChildren(...series.map(key => {
      const item = element('div', '', 'metric');
      item.style.setProperty('--series', colors[key]);
      item.append(element('strong', percent(values[key])), element('span', t(key)));
      return item;
    }));
  }

  function renderTracks() {
    const trial = Number(get('trial').value);
    const last = result.curves.observed.length;
    get('trial-label').textContent = t('trialLabel')(number(trial), number(last), trial >= switchTrial);
    get('tracks').replaceChildren(...['observed', 'rewired'].map(key => {
      const item = element('div', '', 'track');
      item.style.setProperty('--series', colors[key]);
      const sample = result.tracks[key][trial - 1];
      item.append(element('h3', t(key === 'rewired' ? 'control1' : key)));
      for (const [name, route] of [['target', sample.target], ['choice', sample.choice]]) {
        const line = element('p', `${t(name)} · `);
        const odor = element('bdi', odors[result.pair[route]]);
        odor.lang = 'en';
        line.append(odor);
        item.append(line);
      }
      item.append(element('span', t(sample.reward ? 'reward' : 'miss'), sample.reward ? 'outcome' : 'outcome miss'));
      return item;
    }));
    drawPlot('lab-plot', result.curves, trial);
  }

  function renderRun() {
    const start = protocol.phase_trials;
    const width = protocol.early_trials;
    const early = Object.fromEntries(series.map(key => [key, result.curves[key].slice(start, start + width)
      .reduce((sum, value) => sum + value, 0) / width]));
    renderMetrics('lab-metrics', early);
    get('run-status').textContent = t('runStatus')(number(result.episodes));
    renderTracks();
  }

  function renderBenchmark() {
    get('study-count').textContent = t('studyCount')(...[benchmark.pairs, benchmark.episodes, protocol.rewires].map(number));
    get('control-range').textContent = t('controlRange')(...benchmark.control_range.map(percent));
    renderMetrics('study-metrics', Object.fromEntries(series.map(key => [key, benchmark[key].first_after_switch])));
    drawPlot('study-plot', benchmarkCurves);
    get('study-table').replaceChildren(...[...series, 'chance'].map(key => {
      const row = element('tr', '');
      const header = element('th', t(key));
      header.scope = 'row';
      row.append(header, ...['late_before_switch', 'first_after_switch', 'late_after_switch']
        .map(metric => element('td', percent(benchmark[key][metric]))));
      return row;
    }));
  }

  function translate() {
    document.documentElement.lang = language;
    document.documentElement.dir = language === 'fa' ? 'rtl' : 'ltr';
    for (const node of document.querySelectorAll('[data-i]')) node.textContent = t(node.dataset.i);
    const toggle = get('language');
    toggle.lang = language === 'fa' ? 'en' : 'fa';
    toggle.textContent = language === 'fa' ? 'English' : 'فارسی';
    get('odor-count').textContent = number(odors.length);
    get('edge-count').textContent = number(panel.edges);
    get('run-note').textContent = t('runNote');
    get('error').textContent = t('error');
    get('settings').textContent = t('settings')(...[panel.channels, panel.projection_neurons, panel.kenyon_cells,
      protocol.learning_rate, protocol.exploration, protocol.active_fraction].map(number));
    get('sources').replaceChildren(...[
      'https://pmc.ncbi.nlm.nih.gov/articles/PMC9413950/',
      'https://docs.ropensci.org/DoOR.data/reference/door_response_matrix.html',
    ].map((url, i) => {
      const item = element('li', '');
      const link = element('a', t('sourceNames')[i]);
      link.href = url;
      item.append(link);
      return item;
    }));
    renderRun();
    renderBenchmark();
  }

  function run() {
    const pair = [Number(get('odor-a').value), Number(get('odor-b').value)];
    try {
      result = FlyFlipModel.run(data, pair, Number(get('initial').value), get('seed').valueAsNumber);
    } catch (error) {
      if (!(error instanceof RangeError)) throw error;
      get('error').hidden = false;
      return;
    }
    get('error').hidden = true;
    get('trial').max = result.curves.observed.length;
    get('trial').value = 1;
    renderRun();
  }

  ['odor-a', 'odor-b'].forEach((id, j) => {
    const sorted = odors.map((name, i) => [name, i]).sort(([a], [b]) => a.localeCompare(b, 'en'));
    get(id).replaceChildren(...sorted.map(([name, i]) => new Option(name, i)));
    get(id).value = data.initial_pair[j];
  });
  get('seed').value = protocol.seed;
  get('controls').addEventListener('submit', event => { event.preventDefault(); run(); });
  get('language').addEventListener('click', () => { language = language === 'fa' ? 'en' : 'fa'; translate(); });
  get('trial').addEventListener('input', renderTracks);
  get('jump').addEventListener('click', () => { get('trial').value = switchTrial; renderTracks(); });
  window.addEventListener('resize', () => {
    drawPlot('lab-plot', result.curves, Number(get('trial').value));
    drawPlot('study-plot', benchmarkCurves);
  });
  get('download').addEventListener('click', () => {
    const json = JSON.stringify({schema:'flyflip-browser-run-v1',
      benchmark_sha256:data.benchmark_sha256, protocol, sources:data.sources,
      odors:result.pair.map(i => panel.odors[i]), ...result}, null, 2);
    const url = URL.createObjectURL(new Blob([json], {type:'application/json'}));
    const link = element('a', '');
    link.href = url;
    link.download = `flyflip-run-${result.seed}.json`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  run();
  translate();
})();
