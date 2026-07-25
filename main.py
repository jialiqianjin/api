from fastapi import FastAPI, UploadFile, Form, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import httpx
import os
import base64
import asyncio

app = FastAPI()

# 新增底层拦截中间件（最先执行，平台root-path环境下优先处理OPTIONS预检）
class PreflightBlockMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        origin = request.headers.get("origin")
        allow_list = [
            "https://jialiqianjin.l2.ink",
            "https://www.jialiqianjin.l2.ink"
        ]
        if request.method == "OPTIONS":
            resp = Response(status_code=204)
            if origin and origin in allow_list:
                resp.headers["Access-Control-Allow-Origin"] = origin
                resp.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS,PUT,DELETE"
                resp.headers["Access-Control-Allow-Headers"] = "*"
                resp.headers["Access-Control-Max-Age"] = "86400"
            return resp
        response = await call_next(request)
        if origin and origin in allow_list:
            response.headers["Access-Control-Allow-Origin"] = origin
        return response

# 注册底层中间件（优先级最高）
app.add_middleware(PreflightBlockMiddleware)

# 原有CORS配置 完全原样保留，无任何改动
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

AITOOLS_KEY = os.getenv("AITOOLS_KEY")
APP_SECRET = os.getenv("APP_SECRET")
API_ENDPOINT = "https://platform.aitools.cfd/api/v1/chat/completions"
MODEL_ROUTE_LIST = [
    "qwen/qwen2.5-vl-32b",
    "zhipu/glm-4v-flash"
]

@app.get("/ping")
async def ping():
    return {"status": "ok"}

# ========== 文本对话接口 一字未改 ==========
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
            if resp.status_code != 200:
                continue
            raw = resp.json()
            if "choices" in raw and raw["choices"]:
                return raw
        except Exception:
            await asyncio.sleep(0.9)
            continue
    return {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "当前所有模型繁忙，请稍后重新发送"
                }
            }
        ]
    }

# ========== 图片识图接口 一字未改 ==========
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
                        {"type": "image_url", "image_url": f"data:image/jpeg;base64,{b64_img}"},
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
            if res.status_code != 200:
                continue
            raw = res.json()
            if "choices" in raw and raw["choices"]:
                return raw
        except Exception:
            await asyncio.sleep(0.9)
            continue
    return {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "识图请求失败，所有模型暂时无法连接，请稍后尝试"
                }
            }
        ]
    }
