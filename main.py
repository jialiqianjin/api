from fastapi import FastAPI, UploadFile, Form
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
    return {"status": "ok","ver":"fix-v3"}

@app.post("/v1/chat/completions")
async def chat(data: dict):
    token = data.get("token")
    if token != APP_SECRET:
        return {"error": "权限不足"}, 401

    headers = {"Authorization": f"Bearer {MS_KEY}","Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                "https://modelscope.cn/api/v1/services/aigc/text-generation/generation",
                headers=headers,
                json=data
            )
        # 魔搭接口异常处理
        if resp.status_code != 200:
            return {"error": f"魔搭接口异常，状态码:{resp.status_code}"},500
        raw = resp.json()
        content = raw.get("output", {}).get("text", "")
        return {
            "choices": [{"message": {"role": "assistant","content": content}}]
        }
    except Exception as e:
        return {"error": f"请求模型失败：{str(e)}"}, 500

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
    payload = {"model": "qwen-vl-plus","prompt": prompt,"image": b64_img}
    headers = {"Authorization": f"Bearer {MS_KEY}"}
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            res = await client.post(
                "https://modelscope.cn/api/v1/services/aigc/multimodal-generation/generation",
                json=payload,
                headers=headers
            )
        if res.status_code != 200:
            return {"error": f"识图接口异常，状态码:{res.status_code}"},500
        raw = res.json()
        content = raw.get("output", {}).get("text", "")
        return {
            "choices": [{"message": {"role": "assistant","content": content}}]
        }
    except Exception as e:
        return {"error": f"识图请求失败：{str(e)}"}, 500








