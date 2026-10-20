/* ============================================================
   全局交互：加载 / 菜单 / 转场 / 滚动揭示 / 章节巨字与道具注入
   全部原生，无依赖（离线也能跑）
   ============================================================ */
(function () {
  const $  = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.prototype.slice.call(r.querySelectorAll(s));

  /* ---------- 1. 加载遮罩 ---------- */
  function boot() {
    const el = document.getElementById('boot');
    const mark = () => document.documentElement.classList.add('loaded');

    if (!el) { mark(); return; }

    const bar = $('.boot__bar i', el);
    if (bar) { bar.style.transition = 'transform 1s cubic-bezier(.16,.84,.28,1)'; bar.style.transform = 'scaleX(1)'; }

    let fired = false;
    const done = () => {
      if (fired) return; fired = true;
      mark();
      setTimeout(() => { el.classList.add('done'); setTimeout(() => el.remove(), 800); }, 160);
    };

    if (document.readyState === 'complete') setTimeout(done, 380);
    else window.addEventListener('load', () => setTimeout(done, 300));
    setTimeout(done, 2800); // 兜底
  }

  /* ---------- 2. 全屏菜单 ---------- */
  function menu() {
    const el = document.getElementById('menu');
    if (!el) return;
    const open  = () => { el.classList.add('open'); document.body.classList.add('lock'); };
    const close = () => { el.classList.remove('open'); document.body.classList.remove('lock'); };

    const btn = document.getElementById('menuBtn');
    const cls = document.getElementById('menuClose');
    if (btn) btn.addEventListener('click', open);
    if (cls) cls.addEventListener('click', close);
    el.addEventListener('click', e => { if (e.target.tagName === 'A') close(); });
    document.addEventListener('keydown', e => { if (e.key === 'Escape') close(); });
  }

  /* ---------- 3. 页面转场（粉色自下而上） ---------- */
  function transitions() {
    const wipe = document.createElement('div');
    wipe.className = 'wipe';
    document.body.appendChild(wipe);

    $$('a[href]').forEach(a => {
      const href = a.getAttribute('href') || '';
      if (!href || href.charAt(0) === '#' || /^(https?:|mailto:|tel:)/.test(href)) return;
      if (a.target === '_blank') return;
      a.addEventListener('click', e => {
        e.preventDefault();
        wipe.classList.add('on');
        setTimeout(() => { location.href = href; }, 440);
      });
    });

    window.addEventListener('pageshow', e => {
      wipe.classList.remove('on');
      if (e.persisted) document.documentElement.classList.add('loaded');
    });
  }

  /* ---------- 4. 滚动揭示 ---------- */
  function reveal() {
    const items = $$('[data-rev]');
    if (!items.length) return;
    if (!('IntersectionObserver' in window)) { items.forEach(i => i.classList.add('in')); return; }
    const io = new IntersectionObserver((ents) => {
      ents.forEach(en => {
        if (en.isIntersecting) { en.target.classList.add('in'); io.unobserve(en.target); }
      });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });
    items.forEach(i => io.observe(i));
  }

  /* ---------- 5. 章节：巨字 + 道具穿过去 ---------- */
  function chapter() {
    const stage = $('[data-chapter]');
    if (!stage) return;
    const cfg = window.CHAPTERS && window.CHAPTERS[stage.dataset.chapter];
    if (!cfg) return;

    const word = $('.chapter__word', stage);
    if (word) {
      word.innerHTML = cfg.word.split('').map(c => '<span>' + c + '</span>').join('');
    }

    const img = $('.chapter__prop', stage);
    if (img) {
      img.src = window.PROPS[cfg.prop];
      img.alt = cfg.word;
      img.style.setProperty('--px', cfg.px);
      img.style.setProperty('--py', cfg.py);
      img.style.setProperty('--rot', cfg.rot + 'deg');
      img.style.setProperty('--ph', cfg.ph);
      if (cfg.sticker) img.classList.add('chapter__prop--sticker');
    }
  }

  /* ---------- 6. 详情页顶部小道具 ---------- */
  function detailProp() {
    const el = $('[data-prop-cat]');
    if (!el) return;
    const src = (window.PROPS && window.PROPS[window.PROP_BY_CAT[el.dataset.propCat]]) || null;
    if (src) el.src = src;
  }

  /* ---------- 启动 ---------- */
  document.addEventListener('DOMContentLoaded', () => {
    boot(); menu(); chapter(); detailProp();
    if (window.__renderPages) window.__renderPages();
    reveal(); transitions();
  });
})();
