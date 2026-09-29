# 个人主页 · 六日

一个用 HTML + CSS + 原生 JS 写的个人主页，共四屏，外加一个本地 Python 小服务。

```
D:\WorkBuddy\2026-09-29-firstwebsite\
├── index.html      ← 网页本体（四屏：关于我 / 学习记录 / 去背景 / 文生图）
├── avatar.jpg      ← 圆形头像（从「新一寸.jpg」裁出来的）
├── avatar.webp     ← 同上，webp 版，体积更小
├── server.py       ← 本地服务，代理 Replicate 和 OpenRouter（Key 在服务端读环境变量）
├── start.bat       ← 双击它就能启动服务并打开网页
├── make_avatar.py  ← 换头像用的脚本
└── README.md       ← 本文件
```

**四屏分别是：**

| 屏 | 功能 | 需要本地服务吗 | 需要 API Key 吗 |
| --- | --- | --- | --- |
| 一 · 关于我 | 头像、昵称、介绍、兴趣、目标 | 不需要 | 不需要 |
| 一 · 天气（右上角） | 北京实时天气 | 不需要 | 不需要（Open-Meteo 免费） |
| 二 · 我的学习记录 | 时间线 | 不需要 | 不需要 |
| 三 · 一键去除图片背景 | 抠图，出透明 PNG | **需要** | 需要 Replicate |
| 四 · 文字生成图片 | 打字出图 | **需要** | 需要 OpenRouter |

---

## 一、怎么打开

### 只看前三屏（关于我 + 天气 + 学习记录）

**直接双击 `index.html`** 就行。天气也能正常显示，因为它调的是 Open-Meteo
的公开接口，不需要任何 Key。

### 要用第三屏、第四屏

这两屏需要本地服务，**必须双击 `start.bat`**，然后浏览器会自动打开
`http://127.0.0.1:8000`。

> ⚠️ 直接双击 `index.html` 打开时，第三、四屏会提示「连不上本地服务」—— 这是正常的，
> 因为浏览器出于安全限制，不允许 `file://` 页面直接调本地接口。

服务启动后，那个命令行窗口**不要关**，关了服务就停了。

---

## 二、设置两个 API Key

密钥**都不写在代码里**，`server.py` 运行时从系统环境变量读取。

### 1. 申请 Key

| 用途 | 申请地址 | 长什么样 |
| --- | --- | --- |
| 第三屏 · 去背景（Replicate） | <https://replicate.com/account/api-tokens> | `r8_` 开头 |
| 第四屏 · 文生图（OpenRouter） | <https://openrouter.ai/keys> | `sk-or-v1-` 开头 |

两者都是**按用量付费**：Replicate 的 remove-bg 单次约几分钱；
OpenRouter 的 `gpt-5.4-image-2` 实测一张 1:1 的图约 **$0.006**（low 质量）。
建议都去后台设置消费上限。

### 2. 设置环境变量（Windows，一次即可永久生效）

按 `Win + R`，输入 `powershell`，回车，执行（两行分别执行）：

```powershell
setx REPLICATE_API_TOKEN "r8_把这里换成你的"
setx OPENROUTER_API_KEY  "sk-or-v1-把这里换成你的"
```

看到 `成功: 指定的值已保存。` 就好了。

### 3. 验证有没有读到

双击 `start.bat`，看窗口里的这两行：

```
  Replicate Key  : 已读取 ✓
  OpenRouter Key : 已读取 ✓
```

或者浏览器打开 <http://127.0.0.1:8000/api/health> 自检：

```json
{ "ok": true, "token_configured": true, "openrouter_configured": true,
  "model": "lucataco/remove-bg", "image_model": "openai/gpt-5.4-image-2" }
```

> **关于「设置了但读不到」**：`setx` 只对**之后新开的进程**生效。
> 如果启动服务的终端是在 `setx` 之前开的，就读不到。
> 为此 `server.py` 内置了**注册表兜底** —— 环境变量为空时会再去
> `HKCU\Environment` 里读一次，所以这种情况下服务依然能正常工作。
> 最保险的做法还是设置完重开一个窗口。

---

## 三、第三屏「一键去除图片背景」

1. 把图片**拖进虚线框**，或点一下虚线框选择文件（支持 JPG / PNG / WebP，≤ 8 MB）
2. 点 **「去除背景」** —— 按钮会变灰并显示「处理中…」，一般 5～20 秒
3. 下方并排显示**原图**和**结果**。结果那格是棋盘格背景，**棋盘格就代表透明区域**
4. 点 **「下载结果」** 保存成 `原文件名-no-bg.png`（透明背景的 PNG）
5. 点 **「重来」** 清空，换下一张

---

## 四、第四屏「文字生成图片」

界面是 Google 那种极简白底风格：圆角搜索框、蓝色主按钮、大量留白。

1. 在输入框里**写一句描述**（也可以点下面的示例胶囊一键填入）
2. 选好 **比例 / 质量 / 张数**
3. 点 **「生成图片」** —— 按钮变灰显示「生成中…」，通常 **15～60 秒**
4. 出图后每张图片是一张卡片，点卡片里的 **「下载」** 保存 PNG
5. **快捷键**：在输入框里按 `Ctrl + Enter` 直接提交

结果上方会显示模型名、耗时、张数和本次成本（美元）。

### 各选项说明

| 选项 | 可选值 | 说明 |
| --- | --- | --- |
| 比例 | `1:1` `16:9` `9:16` `3:2` `2:3` `4:3` `3:4` `21:9` | 模型的真实能力范围 |
| 质量 | `low` `medium` `high` `auto` | low 最快最便宜；high 最慢最贵 |
| 张数 | 1 / 2 / 4 | 后端最多允许 4 张 |

### 接口选型说明（这一条比较重要）

OpenRouter 上同一个模型有两条可用的路：

| 端点 | 结果 |
| --- | --- |
| `POST /api/v1/chat/completions` | ❌ 在本机所在地区被挡：`403 This model is not available in your region.` |
| `POST /api/v1/images`（专用图像接口） | ✅ 实测可用 |

所以本项目走的是**专用的 `/api/v1/images`**，请求体是
`{ model, prompt, aspect_ratio, quality, output_format, n }`，
返回 `{ data: [{ b64_json, media_type }], usage: { cost } }`。

> 这个坑值得记一下：**一个模型可能有多个可用端点，一条不通不代表模型不可用，
> 换一条路（尤其是厂商专门为图像/语音等模态开的端点）往往就通了。**

---

## 五、想改东西改哪里

### 改颜色（前三屏统一）

打开 `index.html`，`<style>` 最顶上有一块 `:root{ ... }`，改那里的变量就够了：

```css
--c-brand:  #4f6ef7;   /* 主题色：按钮、时间线圆点、标签 */
--c-brand-2:#8b5cf6;   /* 主题渐变终点 */
--c-bg:     #f6f7fb;   /* 页面背景 */
--c-card:   #ffffff;   /* 卡片背景 */
--c-text:   #1f2430;   /* 主文字 */
--avatar-size:150px;   /* 头像直径，手机端自动缩到 118px */
```

第四屏是**故意做成另一套风格**的（Google 极简），它有自己的配色，
在 `.screen--imagen{ ... }` 里，Google 四色是：

```css
--g-blue:#4285f4; --g-red:#ea4335; --g-yellow:#fbbc05; --g-green:#34a853;
```

### 换头像

把你的照片覆盖成同名的 `avatar.jpg` 就行。
或者把新照片放在同目录，改 `make_avatar.py` 里的 `SRC` 路径，再跑一次：

```powershell
C:\Users\Admin\.workbuddy\binaries\python\envs\default\Scripts\python.exe make_avatar.py
```

### 改昵称、一句话介绍、兴趣爱好、学习目标

都在第一屏的 `<section class="screen--hero">` 里：

- 昵称 → `<h1 class="nickname">六日</h1>`
- 介绍 → `<p class="tagline">...</p>`
- 兴趣爱好 → 加一个 `<span class="tag">...</span>` 就多一个标签
- 学习目标 → `<ul class="goal-list">` 里的 `<li>`

### 加一条学习记录

复制整块这段，粘到时间线 `<div class="timeline">` 里，改文字即可：

```html
<article class="entry">
  <div class="entry__card">
    <span class="entry__date">2026 · 10</span>
    <h3 class="entry__title">这一条学了什么</h3>
    <p class="entry__desc">
      具体描述，可以写遇到的问题和怎么解决的。
    </p>
  </div>
</article>
```

想最新的排最上面，就粘到最前面。现在有 5 条（文生图 → 去背景 → API 调用 → 个人网页 → 爬虫）。

### 改第四屏的示例提示词

`<div class="g-examples" id="g-examples">` 里每个 `<button class="g-chip">` 就是一颗胶囊：

```html
<button class="g-chip" type="button" data-p="真正的提示词写这里">按钮上显示的字</button>
```

### 换天气城市

`index.html` 底部第一个 `<script>` 里：

```js
const LATITUDE  = 39.9042;     // 纬度
const LONGITUDE = 116.4074;    // 经度
const CITY_NAME = "北京";       // 显示的城市名
```

### 换模型

**去背景** → `server.py` 顶部：

```python
MODEL_OWNER_NAME = "lucataco/remove-bg"
MODEL_VERSION = "95fcc2a26d3899cd6c2691c900465aaeff466285a65c14638cc5f36f34befaf1"
```

版本 hash 在模型页的 **Versions** 标签里，地址栏最后那段。

**文生图** → `server.py` 顶部：

```python
IMAGE_MODEL = "openai/gpt-5.4-image-2"
```

可以换成别的出图模型，先查它支持哪些参数：

```powershell
curl "https://openrouter.ai/api/v1/images/models"      # 列出所有出图模型
curl "https://openrouter.ai/api/v1/images/models/<id>/endpoints"   # 查某个模型的能力和价格
```

---

## 六、技术说明（为什么不能把 Key 写在前端）

两个功能都是这个结构，全部在 `server.py` 里完成：

```
浏览器 ──① POST /api/xxx（本地）──▶ server.py ──② 带上 Key──▶ 第三方 API
                                        │
浏览器 ◀──③ 返回图片二进制 / base64 ────┘
```

关键点：**浏览器拿不到、也不需要 Key**。鉴权头 `Authorization: Bearer ...`
只在服务端拼接，前端通信的都是本地 `127.0.0.1`。

如果把 Key 直接写在 `index.html` 里，任何人按 F12 看源码就能拿走你的密钥，
然后拿去刷你自己的账单 —— 这是前端调第三方 API 最常见的坑。

`server.py` 只用了标准库 + `requests`，不需要装 Flask，也只监听 `127.0.0.1`
（外网访问不到）。静态文件那部分做了目录穿越防护：请求路径会先
`realpath` 解析再比对前缀，`/../server.py` 之类的路子一律 404。

---

## 七、常见问题

**Q：第三、四屏都提示「连不上本地服务」**
没有启动 `start.bat`，或者你是直接双击 `index.html` 打开的。要双击 `start.bat`，
然后从 `http://127.0.0.1:8000` 访问。

**Q：提示没有找到 XXX_API_KEY，但我明明 setx 过**
设置完之后**要重开窗口**。`server.py` 有注册表兜底，多数情况能自愈；
实在不行就重开一个终端再双击 `start.bat`。

**Q：出图很慢 / 去背景很慢**
正常。第一次调用要冷启动模型，可能 20～30 秒；文生图 high 质量会明显更慢。
两个功能都有超时保护（去背景 180 秒，文生图 300 秒），超时会报错而不是卡死。

**Q：为什么结果图有格子？**
那是「透明背景」的示意图，和 PS 里的灰白格子一样。下载的 PNG 本身是透明的。

**Q：第四屏的比例选项为什么没有 `3:1` 之类的？**
因为那些是模型真实支持的集合，从
`/api/v1/images/models/openai/gpt-5.4-image-2/endpoints` 查到的。
前端也能随便传，后端会安全地夹回默认值。

**Q：端口 8000 被占了怎么办？**
改 `server.py` 里的 `PORT = 8000`，比如换成 `8080`，然后访问
`http://127.0.0.1:8080`。

**Q：换电脑能用吗？**
`index.html` 和 `avatar.jpg` 拷贝过去，双击就能看前三屏。
要用后两屏，得在新电脑上装 Python + `requests`，并重新设置两个环境变量。

---

## 八、备注

- 天气数据：[Open-Meteo](https://open-meteo.com/) · 免费、无需 Key
- 抠图模型：[lucataco/remove-bg](https://replicate.com/lucataco/remove-bg) · 需 Replicate 账号
- 文生图模型：[openai/gpt-5.4-image-2](https://openrouter.ai/openai/gpt-5.4-image-2) · 需 OpenRouter 账号
- 页面无任何外部依赖（不引 CDN、不装 npm 包），前三屏离线也能看
