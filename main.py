from fastapi import FastAPI, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os
import base64
import json

app = FastAPI()

# 前端域名白名单
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

MS_KEY = os.getenv("MS_KEY")
APP_SECRET = os.getenv("APP_SECRET")

@app.get("/ping")
async def ping():
    return {"status": "ok"}

# 文本对话接口
@app.post("/v1/chat/completions")
async def chat(data: dict):
    token = data.get("token")
    if token != APP_SECRET:
        return {"error": "权限不足"}, 401

    headers = {
        "Authorization": f"Bearer {MS_KEY}",
        "Content-Type": "application/json"
    }
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                "https://modelscope.cn/api/v1/services/aigc/text-generation/generation",
                headers=headers,
                json=data
            )
        raw = resp.json()
        # 打印原始返回，方便排查
        print("魔搭文本原始返回：", json.dumps(raw, ensure_ascii=False))
        # 兼容多种返回结构兜底
        content = ""
        if raw.get("output") and raw["output"].get("text"):
            content = raw["output"]["text"]
        elif raw.get("output") and raw["output"].get("choices"):
            content = raw["output"]["choices"][0]["message"]["content"]

        return {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": content
                    }
                }
            ]
        }
    except Exception as e:
        print("文本接口异常：", str(e))
        return {"error": f"请求模型失败：{str(e)}"}, 500

# 图片识图接口
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
    payload = {
        "model": "qwen-vl-plus",
        "prompt": prompt,
        "image": b64_img
    }
    headers = {"Authorization": f"Bearer {MS_KEY}"}
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            res = await client.post(
                "https://modelscope.cn/api/v1/services/aigc/multimodal-generation/generation",
                json=payload,
                headers=headers
            )
        raw = res.json()
        print("魔搭识图原始返回：", json.dumps(raw, ensure_ascii=False))
        content = ""
        if raw.get("output") and raw["output"].get("text"):
            content = raw["output"]["text"]
        elif raw.get("output") and raw["output"].get("choices"):
            content = raw["output"]["choices"][0]["message"]["content"]

        return {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": content
                    }
                }
            ]
        }
    except Exception as e:
        print("识图接口异常：", str(e))
        return {"error": f"识图请求失败：{str(e)}"}, 500








