from fastapi import FastAPI, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os
import base64
import json
import asyncio

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

AQUA_KEY = os.getenv("AQUA_KEY")
APP_SECRET = os.getenv("APP_SECRET")
API_BASE = "https://api.ltzy.top/v1"
# 主模型、备选模型（都支持识图）
MODEL_LIST = [
    "qwen/qwen3.5-397b-a17b",
    "qwen/qwen3-next-80b"
]

@app.get("/ping")
async def ping():
    return {"status": "ok", "ver": "AQUA-retry"}

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
    
    for model in MODEL_LIST:
        payload = {
            "model": model,
            "messages": messages
        }
        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                resp = await client.post(
                    f"{API_BASE}/chat/completions",
                    headers=headers,
                    json=payload
                )
            raw = resp.json()
            return raw
        except Exception:
            await asyncio.sleep(1)
            continue
    return {"error": "所有模型连接失败，上游服务器断开"}, 500

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

    for model in MODEL_LIST:
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}},
                        {"type": "text", "text": prompt}
                    ]
                }
            ]
        }
        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                res = await client.post(
                    f"{API_BASE}/chat/completions",
                    headers=headers,
                    json=payload
                )
            raw = res.json()
            return raw
        except Exception:
            await asyncio.sleep(1)
            continue
    return {"error": "识图请求全部失败，上游服务器断开"}, 500
