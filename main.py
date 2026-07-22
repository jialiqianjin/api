from fastapi import FastAPI, UploadFile, Form, Body
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os
import base64

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

MS_KEY = os.getenv("MS_KEY")
APP_SECRET = os.getenv("APP_SECRET")

@app.get("/ping")
async def ping():
    return {"status": "ok","ver":"qwen2.5-14b-auto-retry"}

@app.post("/v1/chat/completions")
async def chat(data: dict = Body(...)):
    token = data.get("token")
    if token != APP_SECRET:
        return {"error": "权限不足"}, 401

    headers = {
        "Authorization": f"Bearer {MS_KEY}",
        "Content-Type": "application/json"
    }
    upstream_url = "https://api-inference.modelscope.cn/v1/chat/completions"
    payload = {
        "model": "Qwen/Qwen2.5-14B-Instruct",
        "messages": data.get("messages", [])
    }
    max_retry = 3
    for _ in range(max_retry):
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(
                    upstream_url,
                    headers=headers,
                    json=payload
                )
            if resp.status_code != 200:
                continue
            raw = resp.json()
            if raw.get("choices") and len(raw["choices"]) > 0:
                return raw
        except Exception:
            continue
    return {"error": "模型调度繁忙，未能获取回答，请稍后重新发送消息"}, 500

@app.post("/image_chat")
async def image_chat(
    image: UploadFile,
    prompt: str = Form(...),
    token: str = Form(...)
):
    if token != APP_SECRET:
        return {"error": "权限不足"}, 401
    try:
        img_data = await image.read()
        b64_raw = base64.b64encode(img_data).decode()
        data_url = f"data:image/jpeg;base64,{b64_raw}"
        headers = {
            "Authorization": f"Bearer {MS_KEY}",
            "Content-Type": "application/json"
        }
        upstream_url = "https://api-inference.modelscope.cn/v1/chat/completions"
        payload = {
            "model": "Qwen/Qwen2.5-VL-7B-Instruct",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": data_url}}
                    ]
                }
            ]
        }
        async with httpx.AsyncClient(timeout=120) as client:
            res = await client.post(upstream_url, headers=headers, json=payload)
        if res.status_code != 200:
            return {"error": f"识图接口异常，状态码:{res.status_code}"},500
        raw = res.json()
        return raw
    except Exception as e:
        return {"error": f"识图请求失败：{str(e)}"}, 500
