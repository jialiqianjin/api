from fastapi import FastAPI, UploadFile, Form, Body
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

MS_KEY = os.getenv("MS_KEY")
APP_SECRET = os.getenv("APP_SECRET")

@app.get("/ping")
async def ping():
    return {"status": "ok", "ver": "fix-v5"}

# ========== 文本对话接口【修复Body接收问题】==========
@app.post("/v1/chat/completions")
async def chat(data: dict = Body(...)):
    token = data.get("token")
    if token != APP_SECRET:
        return {"error": "权限不足"}, 401

    headers = {"Authorization": f"Bearer {MS_KEY}", "Content-Type": "application/json"}
    try:
        messages = data.get("messages", [])
        payload = {
            "input": {
                "messages": messages
            }
        }
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                "https://modelscope.cn/api/v1/services/aigc/text-generation/generation",
                headers=headers,
                json=payload
            )
        if resp.status_code != 200:
            return {"error": f"魔搭接口异常，状态码:{resp.status_code}"}, 500

        resp_text = resp.text.strip()
        try:
            raw = json.loads(resp_text)
        except json.JSONDecodeError:
            lines = [l for l in resp_text.splitlines() if l.strip()]
            raw = json.loads(lines[-1]) if lines else {}

        content = raw.get("output", {}).get("text", "")
        return {
            "choices": [{"message": {"role": "assistant", "content": content}}]
        }
    except Exception as e:
        return {"error": f"请求模型失败：{str(e)}"}, 500

# ========== 识图接口 ==========
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
        b64_img = base64.b64encode(img_data).decode()
        payload = {
            "model": "qwen-vl-plus",
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"image": b64_img},
                            {"text": prompt}
                        ]
                    }
                ]
            }
        }
        headers = {"Authorization": f"Bearer {MS_KEY}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=120) as client:
            res = await client.post(
                "https://modelscope.cn/api/v1/services/aigc/multimodal-generation/generation",
                json=payload,
                headers=headers
            )
        if res.status_code != 200:
            return {"error": f"识图接口异常，状态码:{res.status_code}"}, 500
        raw = res.json()
        content = raw.get("output", {}).get("text", "")
        return {
            "choices": [{"message": {"role": "assistant", "content": content}}]
        }
    except Exception as e:
        return {"error": f"识图请求失败：{str(e)}"}, 500
