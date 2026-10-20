# 胡晶晶 · 个人站

复刻 trevornoah.com 的交互骨架（Awwwards SOTD 2026-09-03），内容全部换成自己的。
纯静态，双击 `index.html` 即可打开，零依赖安装。

## 设计纪律（三条）

1. **每个章节页 = 一个巨大的粉色词 + 一个 3D 物件从词中间穿过去。** 物件压住字，不飘角落。
2. **物件缩放跟字号走，不跟页面走。** 高度 = 字高 × 系数（`--ph`），窗口缩放时永远成比例。
3. **全站只有三色**：粉 `#FF9BB4` / 深蓝 `#1D2440` / 白。物件是画面里唯一有材质和阴影的东西。

## 页面

| 文件 | 巨词 | 穿过去的物件 | 内容 |
|---|---|---|---|
| `index.html` | 胡晶晶 | — | 首屏只有 wordmark + Menu + 写信药丸；下面 4 个索引段 + Latest 时间线 + 引用块 |
| `work.html` | 作品 | 复古摄影机 | 24 个项目按 7 类分组列表，hover 粉块自下而上扫过 |
| `screen.html` | 影音 | 媒体播放器 | 5 个视听作品，左侧播放器舞台 + 右侧曲目表（可点击切换） |
| `words.html` | 文字 | 一摞书 | 6 篇文字作品卡片，hover 整卡变粉 |
| `about.html` | 关于 | **她本人**（撕纸贴纸 cutout） | 履历六段 + 奖项 + 工具箱 |
| `contact.html` | 联系 | 信封 | 真实邮箱 / 电话 / 状态 |
| `project.html?id=N` | 项目名 | 按分类自动换 | 详情：引言 / 正文 / 元信息 / WHY-METHOD-REFLECT / 上下篇 |

铺垫四次，第五次转身：前四页教你"词中间会有个物件"，翻到关于页，物件是她本人。

## 文件结构

```
assets/
  css/style.css      全部样式。改配色只动 :root 三行
  js/projects.js     24 个项目的全部文案（数据层）
  js/props.js        巨词与物件的配置（哪个词配哪个道具、落点、旋转、大小）
  js/pages.js        列表 / 播放器 / 详情的渲染逻辑
  js/main.js         加载遮罩 / 全屏菜单 / 页面转场 / 滚动揭示
  js/field-gl.js     WebGL 粒子场（手写 GLSL，SDF 三角描边 + 鼠标斥力）
  props/*.png        3D 渲染道具（AI 生成后抠底）
  img/portrait-cut.png  关于页人像（撕纸贴纸，透明底）
```

## 改内容

- **改项目文案** → 只动 `assets/js/projects.js`，一个文件管全站
- **换道具 / 调落点** → 只动 `assets/js/props.js`（`px` 落点、`rot` 旋转、`ph` 相对字高）
- **改配色** → 只动 `style.css` 顶部 `:root` 的三行
- **加项目** → `projects.js` 的 `PROJECTS` 数组加一项，编号顺延

## 技术说明

- **零依赖**：没用 GSAP / jQuery，动画全部 CSS transition + IntersectionObserver。离线也能跑。
- **唯一的外部请求是 Google Fonts**（Noto Sans SC + Archivo）。断网时降级为系统字体（微软雅黑），布局不崩。
- **WebGL 粒子**：2600 个三角，顶点着色器做漂移和鼠标斥力，片元着色器用 SDF 画描边（不是贴图，任何尺寸都干净）。`prefers-reduced-motion` 时只画静态一帧。
- **页面转场**：粉色自下而上盖满（440ms）后跳转，返回时自动复位。

## 已知限制

- 道具 PNG 每张 400–900KB，本地打开无感；**以后部署上线前建议过一遍 TinyPNG**。
- 巨字字体是 Noto Sans SC 900，和原站的 Die Grotesk / Druk 气质有差别——商业字体拿不到，这是最接近的免费替代。
- 项目配图位置留的是文字卡片，等你从作品集 PDF 里导图后接进 `project.html` 的 gallery 即可。
