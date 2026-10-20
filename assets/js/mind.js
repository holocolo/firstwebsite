/* ============================================================
   首页 · 脑海交互
   眼珠跟随鼠标 —— 「眼睛窗口」：每只眼睛一个椭圆裁剪窗，
   窗内是同一张头像按眼距对位，鼠标移动时窗内图像平移，
   瞳孔就在眼裂里转动。遮罩椭圆羽化，看不出接缝。
   幅度经逐像素模拟校准：水平 ±3.0% 头宽（瞳孔贴到眼角），
   垂直 ±1.4%（再大会像眨眼）。
   ============================================================ */
(function () {
  const mind = document.getElementById('mind');
  if (!mind) return;
  const head = mind.querySelector('.mind__head');
  const eyes = Array.from(mind.querySelectorAll('.mind__eye'));
  if (!head || !eyes.length) return;

  /* 源图 860x875。窗口 = 96x60 源像素的椭圆，罩住眼裂（74x42）并留羽化边 */
  const WIN_W = 0.1116;               /* 占头宽比例 */
  const WIN_H_RATIO = 0.625;          /* 窗高 = 窗宽 × 0.625 */
  const AMP_X = 0.030, AMP_Y = 0.014; /* 最大位移，占头宽比例 */

  let placedOk = false;
  function place() {
    const w = head.clientWidth, h = head.clientHeight;
    if (!w || !h) return false;        /* 图片没加载完，交给看门狗重试 */
    const winW = w * WIN_W, winH = winW * WIN_H_RATIO;
    eyes.forEach(el => {
      const ex = +el.dataset.x / 100, ey = +el.dataset.y / 100;
      el.style.width  = winW + 'px';
      el.style.height = winH + 'px';
      el.style.left = (ex * w - winW / 2) + 'px';
      el.style.top  = (ey * h - winH / 2) + 'px';
      const img = el.querySelector('img');
      img.style.width  = w + 'px';
      img.style.height = h + 'px';
      img.style.left = (winW / 2 - ex * w) + 'px';
      img.style.top  = (winH / 2 - ey * h) + 'px';
    });
    placedOk = true;
    return true;
  }
  addEventListener('resize', () => { placedOk = false; place(); }, { passive: true });
  addEventListener('load', () => { placedOk = false; place(); });
  place();
  document.documentElement.classList.add('js-mind');   /* 显示眼睛窗口 */
  eyes.forEach(el => { el.style.display = 'block'; }); /* 双保险 */

  /* 看门狗：字体/布局就位前尺寸可能为 0，逐帧重试；ResizeObserver 兜住后续变化 */
  let tries = 0;
  (function ensure() {
    if (placedOk) return;
    place();
    if (!placedOk && tries++ < 300) requestAnimationFrame(ensure);
  })();
  if (window.ResizeObserver) new ResizeObserver(() => { placedOk = false; place(); }).observe(head);

  /* ---- 眼珠跟随：目标位移按头宽换算，鼠标扫到屏幕边缘 = 瞳孔贴到眼角 ---- */
  let tx = 0, ty = 0, rx = 0, ry = 0, lastMove = 0;
  const clamp = v => Math.max(-1, Math.min(1, v));

  function amp() {
    const w = head.clientWidth || 600;
    return [w * AMP_X, w * AMP_Y];
  }
  function aim(clientX, clientY) {
    const r = head.getBoundingClientRect();
    const cx = r.left + r.width / 2, cy = r.top + r.height * 0.42;
    const nx = clamp((clientX - cx) / (innerWidth * 0.32));
    const ny = clamp((clientY - cy) / (innerHeight * 0.38));
    const [ax, ay] = amp();
    tx = nx * ax; ty = ny * ay;
    lastMove = performance.now();
  }

  const onMove = e => aim(e.clientX, e.clientY);
  addEventListener('pointermove', onMove, { passive: true });
  addEventListener('mousemove', onMove, { passive: true });
  addEventListener('touchmove', e => {
    const t = e.touches[0]; if (t) aim(t.clientX, t.clientY);
  }, { passive: true });

  /* 鼠标静止 5 秒后随机瞟一眼，别像张照片 */
  setInterval(() => {
    if (performance.now() - lastMove < 5000) return;
    const [ax, ay] = amp();
    tx = (Math.random() * 2 - 1) * ax * 0.7;
    ty = (Math.random() * 2 - 1) * ay * 0.7;
  }, 3200);

  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;

  (function loop() {
    const k = reduce ? 1 : 0.18;
    rx += (tx - rx) * k;
    ry += (ty - ry) * k;
    const s = 'translate(' + rx.toFixed(2) + 'px,' + ry.toFixed(2) + 'px)';
    eyes.forEach(el => {
      const img = el.querySelector('img');
      img.style.transform = s;
      img.style.webkitTransform = s;
    });
    /* 跟着视线极轻微地歪一下头 —— 瞳孔位移之外的第二重"她在看你"信号 */
    const [ax] = amp();
    mind.style.transform = 'rotate(' + (rx / ax * 1.2).toFixed(3) + 'deg)';
    requestAnimationFrame(loop);
  })();

  /* 调试用：控制台敲 __mind() 可看当前偏移 */
  window.__mind = () => ({ tx: +tx.toFixed(2), ty: +ty.toFixed(2), rx: +rx.toFixed(2), ry: +ry.toFixed(2), eyes: eyes.length });
})();
