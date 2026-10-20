/* ============================================================
   页面渲染：作品列表 / 影音播放器 / 文字卡片 / 项目详情
   数据全部来自 projects.js，这里只负责拼 DOM
   ============================================================ */
(function () {
  const $  = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.prototype.slice.call(r.querySelectorAll(s));
  const esc = s => String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

  const catFull = key => (CATEGORIES.filter(c => c.key === key)[0] || {}).full || '';
  const byId = n => PROJECTS.filter(p => p.n === n)[0];
  const title0 = p => p.title[0];

  /* ---------- 作品列表：全量，按分类分组 ---------- */
  function renderWork() {
    const host = $('#workList');
    if (!host) return;

    host.innerHTML = CATEGORIES.map(c => {
      const items = PROJECTS.filter(p => p.cat === c.key);
      if (!items.length) return '';
      return '' +
        '<section class="grp">' +
          '<div class="grp__inner">' +
            '<div class="grp__head">' +
              '<span>' + c.no + '</span>' +
              '<h2>' + esc(c.full) + '</h2>' +
              '<p>' + esc(c.blurb) + '</p>' +
            '</div>' +
            '<ul class="rows">' + items.map(rowHTML).join('') + '</ul>' +
          '</div>' +
        '</section>';
    }).join('');
  }

  function rowHTML(p) {
    return '' +
      '<li class="row"><a href="project.html?id=' + p.n + '">' +
        '<span class="row__no">' + p.n + '</span>' +
        '<span class="row__title">' + esc(title0(p)) +
          (p.title[1] ? '<em>' + esc(p.title[1]) + '</em>' : '') + '</span>' +
        '<span class="row__cat">' + esc(catFull(p.cat)) + '</span>' +
        '<span class="row__go">&#8594;</span>' +
      '</a></li>';
  }

  /* ---------- 影音页：播放器 + 曲目表 ---------- */
  const SCREEN_IDS = ['11', '12', '13', '20', '23'];

  function renderScreen() {
    const host = $('#player');
    if (!host) return;
    const list = SCREEN_IDS.map(byId).filter(Boolean);
    if (!list.length) return;

    host.innerHTML = '' +
      '<div class="player">' +
        '<div class="player__stage">' +
          '<img id="pIllo" src="assets/props/player.png" alt="">' +
          '<div class="player__info">' +
            '<span class="player__no" id="pNo"></span>' +
            '<h3 id="pTitle"></h3>' +
            '<p id="pLead"></p>' +
            '<a class="player__go" id="pGo" href="#">查看这个项目 &#8594;</a>' +
          '</div>' +
        '</div>' +
        '<ol class="playlist" id="pList"></ol>' +
      '</div>';

    const pList = $('#pList');
    pList.innerHTML = list.map((p, i) => '' +
      '<li><button type="button" data-id="' + p.n + '"' + (i === 0 ? ' class="is-on"' : '') + '>' +
        '<span class="pl__no">' + p.n + '</span>' +
        '<span class="pl__name">' + esc(title0(p)) + '</span>' +
        '<span class="pl__time">' + esc(p.title[1] || '') + '</span>' +
      '</button></li>').join('');

    const illo = $('#pIllo'), no = $('#pNo'), ti = $('#pTitle'), le = $('#pLead'), go = $('#pGo');
    function select(id) {
      const p = byId(id);
      if (!p) return;
      no.textContent = p.n + ' / ' + catFull(p.cat);
      ti.textContent = title0(p);
      le.textContent = p.lead;
      go.setAttribute('href', 'project.html?id=' + p.n);
      illo.style.opacity = '0';
      setTimeout(() => { illo.style.opacity = ''; }, 180);
      $$('button', pList).forEach(b => b.classList.toggle('is-on', b.dataset.id === id));
    }
    pList.addEventListener('click', e => {
      const b = e.target.closest('button[data-id]');
      if (b) select(b.dataset.id);
    });
    select(list[0].n);
  }

  /* ---------- 文字页：作品卡 ---------- */
  const WORD_IDS = ['01', '02', '04', '16', '17', '18'];

  function renderWords() {
    const host = $('#shelf');
    if (!host) return;
    const list = WORD_IDS.map(byId).filter(Boolean);
    host.innerHTML = list.map(p => '' +
      '<a class="sheet" href="project.html?id=' + p.n + '" data-rev>' +
        '<span class="sheet__no">' + p.n + ' &middot; ' + esc(catFull(p.cat)) + '</span>' +
        '<h3>' + esc(title0(p)) + '</h3>' +
        '<p>' + esc(p.lead) + '</p>' +
        '<span class="sheet__go">读这一篇 &#8594;</span>' +
      '</a>').join('');
  }

  /* ---------- 项目详情 ---------- */
  function renderDetail() {
    const host = $('#detail');
    if (!host) return;
    const id = new URLSearchParams(location.search).get('id') || '01';
    const p = byId(id) || PROJECTS[0];

    document.title = title0(p) + ' · 胡晶晶';

    $('#dNo').textContent  = p.n;
    $('#dCat').textContent = catFull(p.cat);
    $('#dTitle').innerHTML = esc(title0(p)) +
      (p.title[1] ? '<em>' + esc(p.title[1]) + '</em>' : '');
    $('#dLead').textContent = p.lead;
    $('#dBody').innerHTML = '<p>' + esc(p.body) + '</p><p>' + esc(p.body2) + '</p>';
    $('#dFacts').innerHTML = p.facts.map(f =>
      '<div><dt>' + esc(f[0]) + '</dt><dd>' + esc(f[1]) + '</dd></div>').join('');
    $('#dSecs').innerHTML = p.sections.map(s =>
      '<div class="sec"><span class="sec__label">' + esc(s.label) + '</span><p>' + esc(s.body) + '</p></div>').join('');

    const propImg = $('#dProp');
    if (propImg && window.PROPS) {
      const key = (window.PROP_BY_CAT || {})[p.cat];
      if (key) propImg.src = window.PROPS[key];
    }

    const idx = PROJECTS.indexOf(p);
    const prev = PROJECTS[idx - 1], next = PROJECTS[idx + 1];
    const nav = [];
    if (prev) nav.push('<a href="project.html?id=' + prev.n + '"><small>上一个</small><strong>' + esc(title0(prev)) + '</strong></a>');
    if (next) nav.push('<a href="project.html?id=' + next.n + '"><small>下一个</small><strong>' + esc(title0(next)) + '</strong></a>');
    $('#dNav').innerHTML = nav.join('');
  }

  window.__renderPages = function () {
    renderWork(); renderScreen(); renderWords(); renderDetail();
  };
})();
