#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
个人主页本地服务：静态文件 + 「一键去除图片背景」后端。

为什么需要它：
    浏览器里的前端不能安全地保存 Replicate 的 API Key（打开 F12 就看见了）。
    所以 Key 放在这台机器的环境变量 REPLICATE_API_TOKEN 里，由本脚本在服务端读取，
    前端只跟本服务通信，永远接触不到 Key。

启动：
    双击 start.bat（推荐），或手动执行：
        C:\\Users\\Admin\\.workbuddy\\binaries\\python\\envs\\default\\Scripts\\python.exe server.py
    然后浏览器打开  http://127.0.0.1:8000

模型：
    lucataco/remove-bg
    https://replicate.com/lucataco/remove-bg

API 流程（全部在服务端完成）：
    1. POST https://api.replicate.com/v1/files          上传图片，拿到临时 URL
    2. POST https://api.replicate.com/v1/predictions    用 version hash 建任务
    3. GET  {urls.get}                                  轮询直到成功/失败
    4. GET  {output}                                    把结果 PNG 拉回来给前端

只用标准库 + requests，不需要 Flask。
"""

import base64
import json
import mimetypes
import os
import sys
import time
import threading
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

try:
    import requests  # noqa: F401
    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False

# ============================================================================
# ① 配置区
# ============================================================================

HOST = "127.0.0.1"
PORT = 8000                       # 端口被占用就改这里
WEB_ROOT = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------------------
# 读取环境变量的兜底逻辑
# ---------------------------------------------------------------------------
# 背景：setx 写入的变量，只有「在那之后新启动的进程」才看得到。
# 如果启动本服务的那个终端（或父进程）是在 setx 之前开的，
# os.environ 里就是空的 —— 这时再去注册表里捞一次。
# 这样无论是先设 Key 再开窗口，还是先开窗口再设 Key，都能正常工作。
# ---------------------------------------------------------------------------
def _read_env(name):
    """先读进程环境变量，读不到就回退到 Windows 用户级注册表。"""
    value = os.environ.get(name, "").strip()
    if value:
        return value

    if os.name != "nt":
        return ""

    try:
        import winreg
    except ImportError:
        return ""

    # 用户级优先，再看系统级
    for root, sub in (
        (winreg.HKEY_CURRENT_USER, r"Environment"),
        (winreg.HKEY_LOCAL_MACHINE,
         r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
    ):
        try:
            with winreg.OpenKey(root, sub) as key:
                val, _ = winreg.QueryValueEx(key, name)
                if isinstance(val, str) and val.strip():
                    return val.strip()
        except (FileNotFoundError, OSError):
            continue
    return ""


REPLICATE_API = "https://api.replicate.com/v1"

# lucataco/remove-bg 的版本 hash
MODEL_OWNER_NAME = "lucataco/remove-bg"
MODEL_VERSION = "95fcc2a26d3899cd6c2691c900465aaeff466285a65c14638cc5f36f34befaf1"

# ---------------------------------------------------------------------------
# OpenRouter（文字生成图片）
#   Key 同样从环境变量读：OPENROUTER_API_KEY
#   注意：走的是「专用 Image API」/api/v1/images，
#         不是 /api/v1/chat/completions —— 后者在本机所在地区会被
#         OpenAI 的区域限制挡掉（403 This model is not available in your region）。
#   /api/v1/images 实测可用，返回 data[0].b64_json（base64 的 PNG）
# ---------------------------------------------------------------------------
OPENROUTER_IMAGES_API = "https://openrouter.ai/api/v1/images"
IMAGE_MODEL = "openai/gpt-5.4-image-2"
IMAGE_MODEL_LABEL = "GPT-5.4 Image 2"

# 该模型实际支持的宽高比（从 /api/v1/images/models/{id}/endpoints 查到）
ALLOWED_ASPECTS = ["1:1", "3:2", "2:3", "4:3", "3:4", "16:9", "9:16", "21:9", "auto"]
ALLOWED_QUALITY = ["auto", "low", "medium", "high"]
ALLOWED_FORMAT = ["png", "jpeg", "webp"]

MAX_PROMPT_CHARS = 4000          # 提示词长度上限
IMAGE_TIMEOUT = 300              # 出图可能很慢（实测 15–70 秒），给足 5 分钟
IMAGE_MAX_N = 4                  # 一次最多出几张

# 单张图片上限：前端也会限制，这里是第二道防线
MAX_IMAGE_BYTES = 8 * 1024 * 1024            # 8 MB
MAX_BODY_BYTES = 12 * 1024 * 1024            # 12 MB（含 base64 膨胀）

# 轮询设置
POLL_INTERVAL = 1.5              # 每次查询间隔（秒）
POLL_TIMEOUT = 180               # 总超时（秒）
HTTP_TIMEOUT = 60                # 单次 HTTP 请求超时


# ============================================================================
# ② Replicate 调用逻辑
# ============================================================================

class ReplicateError(Exception):
    """调用 Replicate 过程中出现的、可以直白告诉用户的错误。"""

    def __init__(self, message, status=502):
        super().__init__(message)
        self.message = message
        self.status = status


def _auth_headers(extra=None):
    """读取环境变量里的 Token 并生成请求头。"""
    token = _read_env("REPLICATE_API_TOKEN")
    if not token:
        raise ReplicateError(
            "没有找到 REPLICATE_API_TOKEN。请先设置它，然后重启服务。"
            "设置方法见 README.md。",
            status=500,
        )
    headers = {"Authorization": "Bearer " + token}
    if extra:
        headers.update(extra)
    return headers


def _log(msg):
    print("[remove-bg] " + msg, flush=True)


def upload_image(image_bytes, filename, content_type):
    """
    第 1 步：把图片上传到 Replicate，换取一个临时可访问的 URL。
    官方文档：POST https://api.replicate.com/v1/files （multipart/form-data）
    返回的 urls.get 有效期约 1 小时，足够本次任务用完。
    """
    url = REPLICATE_API + "/files"
    files = {
        "content": (filename, image_bytes, content_type or "application/octet-stream"),
    }
    try:
        resp = requests.post(url, headers=_auth_headers(), files=files, timeout=HTTP_TIMEOUT)
    except requests.RequestException as exc:
        raise ReplicateError("连接 Replicate 上传接口失败：%s" % exc)

    if resp.status_code not in (200, 201):
        raise ReplicateError(
            "上传图片失败（HTTP %s）：%s" % (resp.status_code, _short(resp.text))
        )

    data = resp.json()
    file_url = (data.get("urls") or {}).get("get")
    if not file_url:
        raise ReplicateError("上传图片后没有拿到文件 URL：" + _short(resp.text))
    _log("uploaded -> %s" % file_url)
    return file_url


def create_prediction(file_url):
    """
    第 2 步：创建去背景任务。
    用「指定 version hash」的社区模型调用方式，稳定、不受模型改名影响。
    """
    url = REPLICATE_API + "/predictions"
    payload = {
        "version": MODEL_VERSION,
        "input": {"image": file_url},
    }
    try:
        resp = requests.post(
            url,
            headers=_auth_headers({"Content-Type": "application/json"}),
            data=json.dumps(payload),
            timeout=HTTP_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise ReplicateError("创建去背景任务失败：%s" % exc)

    if resp.status_code not in (200, 201):
        detail = _short(resp.text)
        # 401/403 通常是 Token 无效或没额度
        if resp.status_code in (401, 403):
            raise ReplicateError(
                "Replicate 鉴权失败（HTTP %s）。请检查 REPLICATE_API_TOKEN 是否正确、"
                "以及账户是否有可用额度。详情：%s" % (resp.status_code, detail),
                status=401,
            )
        if resp.status_code == 402:
            raise ReplicateError(
                "Replicate 账户额度不足（HTTP 402），请先充值后再试。详情：" + detail,
                status=402,
            )
        raise ReplicateError("创建去背景任务失败（HTTP %s）：%s" % (resp.status_code, detail))

    prediction = resp.json()
    _log("prediction created -> %s" % prediction.get("id"))
    return prediction


def wait_for_prediction(prediction):
    """
    第 3 步：轮询任务状态，直到 succeeded / failed / canceled。
    """
    get_url = (prediction.get("urls") or {}).get("get")
    if not get_url:
        raise ReplicateError("任务响应里缺少轮询地址（urls.get）")

    deadline = time.time() + POLL_TIMEOUT
    while True:
        if prediction.get("status") in ("succeeded", "failed", "canceled"):
            return prediction

        if time.time() > deadline:
            raise ReplicateError(
                "处理超时（超过 %d 秒）。可以稍后重试，或换一张更小的图片。" % POLL_TIMEOUT
            )

        time.sleep(POLL_INTERVAL)
        try:
            resp = requests.get(get_url, headers=_auth_headers(), timeout=HTTP_TIMEOUT)
        except requests.RequestException as exc:
            raise ReplicateError("查询任务状态失败：%s" % exc)
        if resp.status_code != 200:
            raise ReplicateError(
                "查询任务状态失败（HTTP %s）：%s" % (resp.status_code, _short(resp.text))
            )
        prediction = resp.json()


def download_output(output_url):
    """第 4 步：把生成的透明背景 PNG 拉回本地字节。"""
    try:
        resp = requests.get(output_url, timeout=HTTP_TIMEOUT)
    except requests.RequestException as exc:
        raise ReplicateError("下载处理结果失败：%s" % exc)
    if resp.status_code != 200:
        raise ReplicateError("下载处理结果失败（HTTP %s）" % resp.status_code)
    return resp.content


def remove_background(image_bytes, filename, content_type):
    """
    串起完整流程，返回 (结果图片字节, 元信息 dict)。
    任何一步失败都抛 ReplicateError，由 HTTP 层转成 JSON 错误给前端。
    """
    started = time.time()

    file_url = upload_image(image_bytes, filename, content_type)
    prediction = create_prediction(file_url)
    prediction = wait_for_prediction(prediction)

    status = prediction.get("status")
    if status != "succeeded":
        err = prediction.get("error") or "任务未成功（状态：%s）" % status
        raise ReplicateError("去背景失败：%s" % err)

    output = prediction.get("output")
    # 不同模型输出可能是字符串，也可能是列表，这里都兼容
    if isinstance(output, list):
        output = output[0] if output else None
    if not output:
        raise ReplicateError("任务成功但没有返回图片地址")

    result_bytes = download_output(output)
    elapsed = round(time.time() - started, 1)
    _log("done in %ss, %d bytes" % (elapsed, len(result_bytes)))

    return result_bytes, {
        "prediction_id": prediction.get("id"),
        "model": MODEL_OWNER_NAME,
        "elapsed_seconds": elapsed,
    }


# ============================================================================
# ②-B OpenRouter 文生图
# ============================================================================

class OpenRouterError(Exception):
    """调用 OpenRouter 过程中出现的、可以直白告诉用户的错误。"""

    def __init__(self, message, status=502):
        super().__init__(message)
        self.message = message
        self.status = status


def _openrouter_key():
    """从环境变量（含注册表兜底）读取 OpenRouter Key。"""
    key = _read_env("OPENROUTER_API_KEY")
    if not key:
        raise OpenRouterError(
            "没有找到 OPENROUTER_API_KEY。请先设置它，然后重启服务。"
            "设置方法见 README.md。",
            status=500,
        )
    return key


def _clamp(value, allowed, default):
    """把前端传来的值限制在白名单内，避免把垃圾参数转给上游。"""
    return value if value in allowed else default


def generate_image(prompt, aspect_ratio="1:1", quality="auto",
                   output_format="png", n=1):
    """
    调用 OpenRouter 的专用 Image API 生成图片。

    请求：POST https://openrouter.ai/api/v1/images
        { "model": "openai/gpt-5.4-image-2", "prompt": ...,
          "aspect_ratio": "1:1", "quality": "low", "n": 1 }

    响应：{ "data": [ { "b64_json": "<base64 PNG>", "media_type": "image/png" } ],
            "usage": { ..., "cost": 0.006 } }

    返回 (图片列表, 元信息)。图片列表元素是 (bytes, media_type)。
    """
    prompt = (prompt or "").strip()
    if not prompt:
        raise OpenRouterError("提示词不能为空。", status=400)
    if len(prompt) > MAX_PROMPT_CHARS:
        raise OpenRouterError(
            "提示词太长（%d 字），请控制在 %d 字以内。" % (len(prompt), MAX_PROMPT_CHARS),
            status=400,
        )

    aspect_ratio = _clamp(aspect_ratio, ALLOWED_ASPECTS, "1:1")
    quality = _clamp(quality, ALLOWED_QUALITY, "auto")
    output_format = _clamp(output_format, ALLOWED_FORMAT, "png")

    try:
        n = int(n)
    except (TypeError, ValueError):
        n = 1
    n = max(1, min(IMAGE_MAX_N, n))

    payload = {
        "model": IMAGE_MODEL,
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,
        "quality": quality,
        "output_format": output_format,
        "n": n,
    }

    started = time.time()
    _log("openrouter 出图请求：%r aspect=%s quality=%s n=%d"
         % (prompt[:60], aspect_ratio, quality, n))

    try:
        resp = requests.post(
            OPENROUTER_IMAGES_API,
            headers={
                "Authorization": "Bearer " + _openrouter_key(),
                "Content-Type": "application/json",
                # 注意：HTTP 头只能是 latin-1，这里千万别写中文，否则 requests 会抛编码错误
                "HTTP-Referer": "http://127.0.0.1:%d" % PORT,
                "X-Title": "Personal Homepage Text-to-Image",
            },
            data=json.dumps(payload),
            timeout=IMAGE_TIMEOUT,
        )
    except requests.Timeout:
        raise OpenRouterError(
            "出图超时（超过 %d 秒）。图片模型偶尔会很慢，稍后重试或改用更低的 quality。"
            % IMAGE_TIMEOUT,
            status=504,
        )
    except requests.RequestException as exc:
        raise OpenRouterError("连接 OpenRouter 失败：%s" % exc)

    if resp.status_code != 200:
        raise OpenRouterError(
            _explain_openrouter_error(resp.status_code, resp.text),
            status=_map_status(resp.status_code),
        )

    try:
        body = resp.json()
    except ValueError:
        raise OpenRouterError("OpenRouter 返回的不是合法 JSON：" + _short(resp.text))

    items = body.get("data") or []
    images = []
    for it in items:
        b64 = it.get("b64_json")
        if not b64:
            continue
        try:
            raw = base64.b64decode(b64)
        except Exception:
            continue
        if raw:
            images.append((raw, it.get("media_type") or "image/png"))

    if not images:
        raise OpenRouterError("模型没有返回图片。原始响应：" + _short(resp.text))

    usage = body.get("usage") or {}
    elapsed = round(time.time() - started, 1)
    _log("openrouter 出图完成：%d 张，%ss，成本约 $%s"
         % (len(images), elapsed, usage.get("cost")))

    return images, {
        "model": IMAGE_MODEL,
        "elapsed_seconds": elapsed,
        "count": len(images),
        "cost_usd": usage.get("cost"),
        "aspect_ratio": aspect_ratio,
        "quality": quality,
    }


def _map_status(upstream_status):
    """把上游状态码映射成我们自己返回给前端的状态码。"""
    if upstream_status == 401:
        return 401          # Key 无效
    if upstream_status == 402:
        return 402          # 余额不足
    if upstream_status == 429:
        return 429          # 限流
    if upstream_status == 400:
        return 400          # 参数问题
    return 502


def _explain_openrouter_error(status, raw_text):
    """把 OpenRouter 的错误翻译成用户能看懂的中文提示。"""
    msg = ""
    try:
        msg = (json.loads(raw_text).get("error") or {}).get("message") or ""
    except Exception:
        msg = _short(raw_text)

    if status == 401:
        return "OpenRouter 鉴权失败（HTTP 401）。请检查 OPENROUTER_API_KEY 是否正确、是否已失效。" \
               "详情：" + _short(msg or raw_text)
    if status == 402:
        return "OpenRouter 账户余额不足（HTTP 402），请先充值。详情：" + _short(msg or raw_text)
    if status == 429:
        return "请求太频繁被限流（HTTP 429），等几秒再试。详情：" + _short(msg or raw_text)
    if status == 403:
        return "该模型在你所在地区不可用（HTTP 403）。详情：" + _short(msg or raw_text)
    if status == 400:
        return "请求参数有问题（HTTP 400）。详情：" + _short(msg or raw_text)
    return "出图失败（HTTP %s）：%s" % (status, _short(msg or raw_text))


# ============================================================================
# ③ HTTP 服务
# ============================================================================

def _short(text, limit=300):
    """把上游返回的长文本截短，避免把一坨 JSON 糊到页面上。"""
    if not text:
        return "(空响应)"
    text = str(text).replace("\n", " ").strip()
    return text if len(text) <= limit else text[:limit] + "…"


class Handler(BaseHTTPRequestHandler):
    server_version = "PersonalHomepage/1.0"

    # ------------------------------------------------------------------ 工具

    def _send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_bytes(self, data, content_type="application/octet-stream", status=200, extra=None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def _error(self, message, status=500):
        self._send_json({"ok": False, "error": message}, status=status)

    def log_message(self, fmt, *args):
        # 精简访问日志，只保留我们关心的
        sys.stdout.write("  %s - %s\n" % (self.address_string(), fmt % args))
        sys.stdout.flush()

    # ------------------------------------------------------------------ GET

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path

        if path == "/api/health":
            token_ok = bool(_read_env("REPLICATE_API_TOKEN"))
            or_ok = bool(_read_env("OPENROUTER_API_KEY"))
            self._send_json({
                "ok": True,
                "token_configured": token_ok,
                "openrouter_configured": or_ok,
                "model": MODEL_OWNER_NAME,
                "image_model": IMAGE_MODEL,
            })
            return

        if path in ("/", "/index.html"):
            self._serve_static("index.html")
            return

        # 其余当作静态文件
        self._serve_static(path.lstrip("/"))

    def _serve_static(self, rel_path):
        """
        提供静态文件。这里只允许访问 WEB_ROOT 内部的文件：
        把请求路径规范化 + 解析软链接之后，必须仍然位于 WEB_ROOT 之下，
        否则一律 404 —— 防止用 ../../ 之类的路径读走 server.py 等文件。
        """
        # 统一分隔符，避免 Windows 下 / 和 \ 混用绕过前缀比较
        rel_path = rel_path.replace("\\", "/")
        if not rel_path or rel_path.endswith("/"):
            rel_path += "index.html"

        root = os.path.realpath(WEB_ROOT)
        target = os.path.realpath(os.path.join(root, rel_path))

        # 用「共同前缀 + 分隔符」判断，避免 /root2 被 /root 误判为内部路径
        if target != root and not target.startswith(root + os.sep):
            self._error("页面不存在：" + rel_path, status=404)
            return
        if not os.path.isfile(target):
            self._error("页面不存在：" + rel_path, status=404)
            return

        safe_path = target  # 后面统一用解析后的真实路径读取

        ctype = mimetypes.guess_type(safe_path)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/javascript", "application/json"):
            ctype += "; charset=utf-8"

        try:
            with open(safe_path, "rb") as fh:
                data = fh.read()
        except OSError as exc:
            self._error("读取文件失败：%s" % exc, status=500)
            return
        self._send_bytes(data, ctype)

    # ------------------------------------------------------------------ POST

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path

        if path == "/api/remove-bg":
            self._handle_remove_bg()
            return

        if path == "/api/generate-image":
            self._handle_generate_image()
            return

        self._error("未知接口：" + path, status=404)

    def _handle_generate_image(self):
        """接收 { prompt, aspect_ratio, quality, output_format, n }，返回图片。"""
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0

        if length <= 0:
            self._error("请求体为空", status=400)
            return
        if length > 256 * 1024:
            self._error("请求体过大", status=413)
            return

        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception as exc:
            self._error("请求体解析失败：%s" % exc, status=400)
            return

        try:
            images, meta = generate_image(
                prompt=payload.get("prompt"),
                aspect_ratio=payload.get("aspect_ratio") or "1:1",
                quality=payload.get("quality") or "auto",
                output_format=payload.get("output_format") or "png",
                n=payload.get("n") or 1,
            )
        except OpenRouterError as exc:
            _log("出图失败：%s" % exc.message)
            self._error(exc.message, status=exc.status)
            return
        except Exception as exc:
            _log("出图未预期错误：%r" % exc)
            self._error("服务端出现未预期错误：%s" % exc, status=500)
            return

        # 默认把第一张作为二进制 PNG 直接返回；
        # 若请求里要了多张（n>1），改成返回 JSON（前端按 base64 展示）。
        if meta["count"] == 1 and not payload.get("as_json"):
            raw, media_type = images[0]
            self._send_bytes(
                raw,
                media_type,
                extra={
                    "X-Model": meta["model"],
                    "X-Elapsed": str(meta["elapsed_seconds"]),
                    "X-Cost-Usd": str(meta.get("cost_usd")),
                    "Access-Control-Expose-Headers": "X-Model, X-Elapsed, X-Cost-Usd",
                },
            )
            return

        self._send_json({
            "ok": True,
            "model": meta["model"],
            "elapsed_seconds": meta["elapsed_seconds"],
            "cost_usd": meta.get("cost_usd"),
            "aspect_ratio": meta["aspect_ratio"],
            "images": [
                {"b64": base64.b64encode(raw).decode("ascii"), "media_type": mt}
                for raw, mt in images
            ],
        })

    def _handle_remove_bg(self):
        # ---- 1. 读取请求体（JSON：{ image: "data:image/png;base64,..." }）----
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0

        if length <= 0:
            self._error("请求体为空", status=400)
            return
        if length > MAX_BODY_BYTES:
            self._error("图片太大（超过 %d MB）" % (MAX_BODY_BYTES // 1024 // 1024), status=413)
            return

        try:
            raw = self.rfile.read(length)
            payload = json.loads(raw.decode("utf-8"))
        except Exception as exc:
            self._error("请求体解析失败：%s" % exc, status=400)
            return

        data_uri = payload.get("image") or ""
        filename = payload.get("filename") or "upload.png"

        # ---- 2. 解析 data URI ----
        if not data_uri.startswith("data:"):
            self._error("image 需要是 data:image/...;base64,... 格式", status=400)
            return

        try:
            header, b64 = data_uri.split(",", 1)
            content_type = header[5:].split(";")[0] or "image/png"
            image_bytes = base64.b64decode(b64)
        except Exception as exc:
            self._error("图片解码失败：%s" % exc, status=400)
            return

        if not image_bytes:
            self._error("图片内容为空", status=400)
            return
        if len(image_bytes) > MAX_IMAGE_BYTES:
            self._error("图片太大（超过 %d MB）" % (MAX_IMAGE_BYTES // 1024 // 1024), status=413)
            return

        _log("收到图片 %s, %.2f MB, %s" % (filename, len(image_bytes) / 1024 / 1024, content_type))

        # ---- 3. 调用 Replicate ----
        try:
            result_bytes, meta = remove_background(image_bytes, filename, content_type)
        except ReplicateError as exc:
            _log("失败：%s" % exc.message)
            self._error(exc.message, status=exc.status)
            return
        except Exception as exc:                      # 兜底，别让服务挂掉
            _log("未预期错误：%r" % exc)
            self._error("服务端出现未预期错误：%s" % exc, status=500)
            return

        # ---- 4. 直接回 PNG 二进制，前端转成 Blob 显示 ----
        self._send_bytes(
            result_bytes,
            "image/png",
            extra={
                "X-Prediction-Id": str(meta.get("prediction_id") or ""),
                "X-Model": meta.get("model") or MODEL_OWNER_NAME,
                "X-Elapsed": str(meta.get("elapsed_seconds") or ""),
                "Access-Control-Expose-Headers": "X-Prediction-Id, X-Model, X-Elapsed",
            },
        )


# ============================================================================
# ④ 启动
# ============================================================================

def main():
    os.chdir(WEB_ROOT)

    if not _HAS_REQUESTS:
        print("缺少 requests 库。请先执行：")
        print('  "%s" -m pip install requests' % sys.executable)
        return 1

    token_ok = bool(_read_env("REPLICATE_API_TOKEN"))
    or_ok = bool(_read_env("OPENROUTER_API_KEY"))

    print("=" * 62)
    print("  个人主页本地服务")
    print("=" * 62)
    print("  网页地址 : http://%s:%d" % (HOST, PORT))
    print("  去背景   : POST /api/remove-bg       (%s)" % MODEL_OWNER_NAME)
    print("  文生图   : POST /api/generate-image  (%s)" % IMAGE_MODEL)
    print("  Replicate Key  : %s" % ("已读取 ✓" if token_ok else "未设置 ✗"))
    print("  OpenRouter Key : %s" % ("已读取 ✓" if or_ok else "未设置 ✗"))
    if not token_ok or not or_ok:
        print()
        print("  缺哪个就设哪个（PowerShell，永久生效，之后要重开窗口）：")
        if not token_ok:
            print('    setx REPLICATE_API_TOKEN "r8_你的token"')
            print("    → https://replicate.com/account/api-tokens")
        if not or_ok:
            print('    setx OPENROUTER_API_KEY "sk-or-v1-你的key"')
            print("    → https://openrouter.ai/keys")
    print()
    print("  按 Ctrl+C 停止服务")
    print("=" * 62)
    print()

    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止。")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
