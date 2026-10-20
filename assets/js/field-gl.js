/* ============================================================
   粒子场 —— 手写 WebGL，零依赖
   2600 个三角形，片元着色器用 SDF 画描边（不是贴图，任何尺寸都干净）
   自主漂移 + 上浮 + 鼠标斥力
   ============================================================ */
(function () {
  const cvs = document.getElementById('field');
  if (!cvs) return;

  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const gl = cvs.getContext('webgl', { alpha: true, antialias: true, premultipliedAlpha: false });
  if (!gl) { cvs.style.display = 'none'; return; }

  const VS = `
  attribute vec2 a_corner;
  attribute vec2 a_seed;
  attribute float a_size;
  attribute float a_phase;
  attribute vec3 a_color;
  uniform float u_time;
  uniform vec2  u_res;
  uniform vec2  u_mouse;
  varying vec2  v_loc;
  varying vec3  v_color;
  varying float v_alpha;

  void main(){
    float sp = 0.010 + a_size * 0.0035;
    float y = fract(a_seed.y - u_time * sp);
    float x = fract(a_seed.x + sin(u_time * 0.06 + a_phase) * 0.018);
    vec2 pos = vec2(x, y) * u_res;

    vec2 d = pos - u_mouse * u_res;
    float dist = length(d) + 0.0001;
    float push = smoothstep(280.0, 0.0, dist);
    pos += (d / dist) * push * 130.0 * (0.4 + a_size * 0.06);

    vec2 world = pos + a_corner * a_size;
    vec2 ndc = (world / u_res) * 2.0 - 1.0;
    gl_Position = vec4(ndc.x, -ndc.y, 0.0, 1.0);

    v_loc   = a_corner;
    v_color = a_color;
    v_alpha = 0.26 + 0.40 * abs(sin(u_time * 0.45 + a_phase));
  }`;

  const FS = `
  precision mediump float;
  varying vec2  v_loc;
  varying vec3  v_color;
  varying float v_alpha;

  float sdTri(vec2 p, float r){
    const float k = 1.7320508;
    p.x = abs(p.x) - r;
    p.y = p.y + r / k;
    if (p.x + k * p.y > 0.0) p = vec2(p.x - k * p.y, -k * p.x - p.y) / 2.0;
    p.x -= clamp(p.x, -2.0 * r, 0.0);
    return -length(p) * sign(p.y);
  }

  void main(){
    float d = sdTri(v_loc, 0.5);
    float aa = fwidth(d) * 1.2 + 0.015;
    float line = 1.0 - smoothstep(0.0, 0.115 + aa, abs(d));
    if (line < 0.03) discard;
    gl_FragColor = vec4(v_color, v_alpha * line);
  }`;

  function sh(type, src) {
    const s = gl.createShader(type);
    gl.shaderSource(s, src); gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) { console.warn('shader', gl.getShaderInfoLog(s)); return null; }
    return s;
  }
  const prog = gl.createProgram();
  const v = sh(gl.VERTEX_SHADER, VS), f = sh(gl.FRAGMENT_SHADER, FS);
  if (!v || !f) { cvs.style.display = 'none'; return; }
  gl.attachShader(prog, v); gl.attachShader(prog, f); gl.linkProgram(prog);
  if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) { console.warn(gl.getProgramInfoLog(prog)); cvs.style.display = 'none'; return; }
  gl.useProgram(prog);

  const PALETTE = [
    [1.0, 0.61, 0.71],   // 粉
    [1.0, 1.0, 1.0],     // 白
    [1.0, 0.61, 0.71],
    [0.80, 0.86, 1.0],
    [1.0, 1.0, 1.0],
    [1.0, 0.74, 0.82]
  ];

  const COUNT = reduce ? 900 : 2600;
  const CORNERS = [-1,-1, 1,-1, -1,1, -1,1, 1,-1, 1,1];

  const corner = new Float32Array(COUNT * 12);
  const seed   = new Float32Array(COUNT * 12);
  const size   = new Float32Array(COUNT * 6);
  const phase  = new Float32Array(COUNT * 6);
  const color  = new Float32Array(COUNT * 18);

  for (let i = 0; i < COUNT; i++) {
    const big = Math.random() < 0.08;
    const s = big ? 6 + Math.random() * 8 : 1.1 + Math.random() * 2.2;
    const sx = Math.random(), sy = Math.random();
    const ph = Math.random() * 6.283;
    const c = PALETTE[(Math.random() * PALETTE.length) | 0];
    for (let k = 0; k < 6; k++) {
      corner[i*12 + k*2] = CORNERS[k*2];
      corner[i*12 + k*2 + 1] = CORNERS[k*2 + 1];
      seed[i*12 + k*2] = sx;
      seed[i*12 + k*2 + 1] = sy;
      size[i*6 + k] = s;
      phase[i*6 + k] = ph;
      color[i*18 + k*3] = c[0];
      color[i*18 + k*3 + 1] = c[1];
      color[i*18 + k*3 + 2] = c[2];
    }
  }

  function buf(data) {
    const b = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, b);
    gl.bufferData(gl.ARRAY_BUFFER, data, gl.STATIC_DRAW);
    return b;
  }
  function attr(name, data, n) {
    const loc = gl.getAttribLocation(prog, name);
    if (loc < 0) return;
    gl.bindBuffer(gl.ARRAY_BUFFER, buf(data));
    gl.enableVertexAttribArray(loc);
    gl.vertexAttribPointer(loc, n, gl.FLOAT, false, 0, 0);
  }
  attr('a_corner', corner, 2);
  attr('a_seed',   seed,   2);
  attr('a_size',   size,   1);
  attr('a_phase',  phase,  1);
  attr('a_color',  color,  3);

  const uTime  = gl.getUniformLocation(prog, 'u_time');
  const uRes   = gl.getUniformLocation(prog, 'u_res');
  const uMouse = gl.getUniformLocation(prog, 'u_mouse');

  let W = 0, H = 0, DPR = 1;
  const mouse = { x: .5, y: .5, tx: .5, ty: .5 };

  function resize() {
    DPR = Math.min(devicePixelRatio || 1, 2);
    W = innerWidth; H = innerHeight;
    cvs.width = Math.floor(W * DPR); cvs.height = Math.floor(H * DPR);
    gl.viewport(0, 0, cvs.width, cvs.height);
    gl.uniform2f(uRes, W, H);
  }

  gl.enable(gl.BLEND);
  gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
  gl.clearColor(0, 0, 0, 0);

  let raf = 0, t0 = performance.now();
  function frame(now) {
    const t = (now - t0) / 1000;
    mouse.x += (mouse.tx - mouse.x) * 0.06;
    mouse.y += (mouse.ty - mouse.y) * 0.06;

    gl.clear(gl.COLOR_BUFFER_BIT);
    gl.uniform1f(uTime, t);
    gl.uniform2f(uMouse, mouse.x, mouse.y);
    gl.drawArrays(gl.TRIANGLES, 0, COUNT * 6);

    if (!reduce) raf = requestAnimationFrame(frame);
  }

  addEventListener('resize', resize, { passive: true });
  addEventListener('mousemove', e => {
    mouse.tx = e.clientX / innerWidth; mouse.ty = e.clientY / innerHeight;
  }, { passive: true });

  resize();
  if (reduce) frame(t0 + 16); else raf = requestAnimationFrame(frame);
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) cancelAnimationFrame(raf);
    else if (!reduce) { t0 = performance.now() - 16; raf = requestAnimationFrame(frame); }
  });
})();
