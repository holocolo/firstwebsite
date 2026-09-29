# -*- coding: utf-8 -*-
"""把一寸照裁成正方形并压缩，生成 avatar.jpg / avatar.webp"""
import os
from PIL import Image

SRC = r"D:\firstwebsite\新一寸.jpg"
OUT_DIR = r"D:\WorkBuddy\2026-09-29-firstwebsite"
os.makedirs(OUT_DIR, exist_ok=True)

img = Image.open(SRC)
img = img.convert("RGB")
w, h = img.size
print("original:", w, "x", h)

# 以图片上方 42% 处为视觉中心裁剪正方形（人像头部通常在上半部分，避免裁到下巴以下太多）
center_x = w // 2
center_y = int(h * 0.42)
side = min(w, h)
left = max(0, center_x - side // 2)
top = max(0, center_y - side // 2)
right = left + side
bottom = top + side
if right > w:
    right = w
    left = w - side
if bottom > h:
    bottom = h
    top = h - side
print("crop box:", left, top, right, bottom)

face = img.crop((left, top, right, bottom)).resize((480, 480), Image.LANCZOS)

jpg_path = os.path.join(OUT_DIR, "avatar.jpg")
webp_path = os.path.join(OUT_DIR, "avatar.webp")
face.save(jpg_path, "JPEG", quality=88, optimize=True, progressive=True)
face.save(webp_path, "WEBP", quality=88, method=6)

for p in (jpg_path, webp_path):
    print(os.path.basename(p), round(os.path.getsize(p) / 1024, 1), "KB")
