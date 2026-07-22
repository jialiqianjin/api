from fastapi import FastAPI, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os
import base64
import json

app = FastAPI()

ALLOW_ORIGINS = [
    "https://jialiqianjin.l2.ink",
    "https://www.jialiqianjin.l2.ink"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 环境变量修改！！不再使用MS_KEY，改为AQUA_KEY
AQUA_KEY = os.getenv("AQUA_KEY")
APP_SECRET = os.getenv("APP_SECRET")
# 选定模型名称
TARGET_MODEL = "qwen/qwen3.5-397b-a17b"
API_BASE = "https://api.ltzy.top/v1"

@app.get("/ping")
async def ping():
    return {"status": "ok", "ver": "AQUA-Qwen3.5-397B"}

# ========== 文本对话接口 ==========
@app.post("/v1/chat/completions")
async def chat(data: dict):
    token = data.get("token")
    if token != APP_SECRET:
        return {"error": "权限不足"}, 401

    headers = {
        "Authorization": f"Bearer {AQUA_KEY}",
        "Content-Type": "application/json"
    }
    messages = data.get("messages", [])
    payload = {
        "model": TARGET_MODEL,
        "messages": messages
    }
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{API_BASE}/chat/completions",
                headers=headers,
                json=payload
            )
        raw = resp.json()
        return raw
    except Exception as e:
        return {"error": f"请求模型失败：{str(e)}"}, 500

# ========== 图片识图接口 ==========
@app.post("/image_chat")
async def image_chat(
    image: UploadFile,
    prompt: str = Form(...),
    token: str = Form(...)
):
    if token != APP_SECRET:
        return {"error": "权限不足"}, 401

    img_data = await image.read()
    b64_img = base64.b64encode(img_data).decode()
    headers = {
        "Authorization": f"Bearer {AQUA_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": TARGET_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image;base64,{b64_img}"}},
                    {"type": "text", "text": prompt}
                ]
            }
        ]
    }
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            res = await client.post(
                f"{API_BASE}/chat/completions",
                headers=headers,
                json=payload
            )
        raw = res.json()
        return raw
    except Exception as e:
        return {"error": f"识图请求失败：{str(e)}"}, 500
