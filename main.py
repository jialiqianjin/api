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

# 环境变量配置
AITOOLS_KEY = os.getenv("AITOOLS_KEY")
APP_SECRET = os.getenv("APP_SECRET")
API_ENDPOINT = "https://platform.aitools.cfd/api/v1/chat/completions"

# 模型轮换队列【主模型→兜底模型】
MODEL_ROUTE_LIST = [
    "qwen/qwen2.5-vl-32b",
    "zhipu/glm-4v-flash"
]

@app.get("/ping")
async def ping():
    return {"status": "ok", "version": "auto-switch-vl"}

# ========== 文本对话接口 ==========
@app.post("/v1/chat/completions")
async def chat(data: dict):
    token = data.get("token")
    if token != APP_SECRET:
        return {"error": "权限不足"}, 401

    headers = {
        "Authorization": f"Bearer {AITOOLS_KEY}",
        "Content-Type": "application/json"
    }
    messages = data.get("messages", [])

    for model_name in MODEL_ROUTE_LIST:
        payload = {
            "model": model_name,
            "messages": messages,
            "max_tokens": 1024,
            "temperature": 0.7
        }
        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                resp = await client.post(
                    API_ENDPOINT,
                    headers=headers,
                    json=payload
                )
            result = resp.json()
            return result
        except Exception:
            await asyncio.sleep(0.9)
            continue

    return {"error": "所有视觉模型请求失败，请稍后重试"}, 500

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
        "Authorization": f"Bearer {AITOOLS_KEY}",
        "Content-Type": "application/json"
    }

    for model_name in MODEL_ROUTE_LIST:
        payload = {
            "model": model_name,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}},
                        {"type": "text", "text": prompt}
                    ]
                }
            ],
            "max_tokens": 1024,
            "temperature": 0.7
        }
        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                res = await client.post(
                    API_ENDPOINT,
                    headers=headers,
                    json=payload
                )
            result = res.json()
            return result
        except Exception:
            await asyncio.sleep(0.9)
            continue

    return {"error": "识图：所有模型连接失败，请稍后尝试"}, 500
