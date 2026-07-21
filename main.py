from fastapi import FastAPI, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os
import base64

app = FastAPI()

# 填入你的前端域名
ALLOW_ORIGINS = ["https://jialiqianjin.l2.ink"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 环境变量读取密钥，禁止硬编码
MS_KEY = os.getenv("MS_KEY")
APP_SECRET = os.getenv("APP_SECRET")

# 保活健康检测接口
@app.get("/ping")
async def ping():
    return {"status": "ok"}

# OpenAI兼容对话接口
@app.post("/v1/chat/completions")
async def chat(data: dict):
    token = data.get("token")
    if token != APP_SECRET:
        return {"error": "权限不足"}, 401
    headers = {
        "Authorization": f"Bearer {MS_KEY}",
        "Content-Type": "application/json"
    }
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            "https://modelscope.cn/api/v1/services/aigc/text-generation/generation",
            headers=headers,
            json=data
        )
    return resp.json()

# 图片识图接口
@app.post("/image_chat")
async def image_chat(prompt: str = Form(...), image: UploadFile, token: str = Form(...)):
    if token != APP_SECRET:
        return {"error": "权限不足"}, 401
    img_data = await image.read()
    b64_img = base64.b64encode(img_data).decode()
    payload = {
        "model": "qwen-vl-plus",
        "prompt": prompt,
        "image": b64_img
    }
    headers = {"Authorization": f"Bearer {MS_KEY}"}
    async with httpx.AsyncClient(timeout=120) as client:
        res = await client.post(
            "https://modelscope.cn/api/v1/services/aigc/multimodal-generation/generation",
            json=payload, headers=headers
        )
    return res.json()



