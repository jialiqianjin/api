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

MS_KEY = os.getenv("MS_KEY")
APP_SECRET = os.getenv("APP_SECRET")
# 识图轮询双模型
VL_MODEL_LIST = ["qwen-vl-max", "qwen-vl-plus"]
# 文本更换为 qwen-turbo（低负载备选）
TEXT_MODEL_LIST = ["qwen-turbo"]

@app.get("/ping")
async def ping():
    return {"status": "ok", "ver": "turbo-text_vlmax"}

# ========== 文本对话接口 ==========
@app.post("/v1/chat/completions")
async def chat(data: dict):
    token = data.get("token")
    if token != APP_SECRET:
        return {"error": "权限不足"}, 401

    headers = {"Authorization": f"Bearer {MS_KEY}", "Content-Type": "application/json"}
    messages = data.get("messages", [])

    for model in TEXT_MODEL_LIST:
        try:
            payload = {
                "model": model,
                "input": {"messages": messages}
            }
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(
                    "https://modelscope.cn/api/v1/services/aigc/text-generation/generation",
                    headers=headers,
                    json=payload
                )
            if resp.status_code != 200:
                continue
            resp_text = resp.text.strip()
            raw = json.loads(resp_text)
            content = raw["output"].get("text", "")
            return {"choices": [{"message": {"role": "assistant", "content": content}}]}
        except Exception:
            continue
    return {"error": "文本模型请求繁忙，请稍后重试"}, 500

# ========== 识图接口【自动切换两个VL模型重试】==========
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
    headers = {"Authorization": f"Bearer {MS_KEY}", "Content-Type": "application/json"}

    for model_name in VL_MODEL_LIST:
        try:
            payload = {
                "model": model_name,
                "input": {
                    "messages": [
                        {
                            "role": "user",
                            "content": [{"image": b64_img}, {"text": prompt}]
                        }
                    ]
                }
            }
            async with httpx.AsyncClient(timeout=120) as client:
                res = await client.post(
                    "https://modelscope.cn/api/v1/services/aigc/multimodal-generation/generation",
                    json=payload,
                    headers=headers
                )
            if res.status_code != 200:
                continue
            raw = res.json()
            content = raw["output"].get("text", "")
            return {"choices": [{"message": {"role": "assistant", "content": content}}]}
        except Exception:
            continue
    return {"error": "qwen-vl-max、qwen-vl-plus 全部繁忙，稍后再试"}, 500












