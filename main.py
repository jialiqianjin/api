from fastapi import FastAPI, UploadFile, Form, Request, Response
import httpx
import os
import base64
import asyncio
app = FastAPI()

# 新增优先处理OPTIONS中间件（唯一改动，其余不动）
@app.middleware("http")
async def preflight_middleware(request: Request, call_next):
    origin = request.headers.get("origin")
    allow_list = [
        "https://jialiqianjin.l2.ink",
        "https://www.jialiqianjin.l2.ink"
    ]
    response: Response = await call_next(request)
    if origin and origin in allow_list:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS,PUT,DELETE"
        response.headers["Access-Control-Allow-Headers"] = "*"
        response.headers["Access-Control-Max-Age"] = "86400"
    # 预检请求直接返回204，不走路由匹配避免404
    if request.method == "OPTIONS":
        return Response(status_code=204)
    return {}

# =========【全局OPTIONS路由保留，兼容兜底，原有代码不动】=========
@app.options("/{full_path:path}")
async def global_options_handler(request: Request, full_path: str):
    return {}

# CORS跨域配置（原样保留不修改）
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
# 文本对话接口（完全原样）
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
# 图片识图接口（完全原样）
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
