from fastapi import FastAPI, UploadFile, Form, Request, Response
# 修复：补充缺失的CORS中间件导入
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os
import base64
import asyncio

app = FastAPI()

# 标准CORS优先注册（最外层中间件，预检优先处理）
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

# 自定义全局预检中间件（修复执行顺序BUG）
@app.middleware("http")
async def preflight_middleware(request: Request, call_next):
    origin = request.headers.get("origin")
    allow_list = [
        "https://jialiqianjin.l2.ink",
        "https://www.jialiqianjin.l2.ink"
    ]
    # 预检请求直接返回204，不进入路由匹配，彻底解决404
    if request.method == "OPTIONS":
        resp = Response(status_code=204)
        if origin and origin in allow_list:
            resp.headers["Access-Control-Allow-Origin"] = origin
            resp.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS,PUT,DELETE"
            resp.headers["Access-Control-Allow-Headers"] = "*"
            resp.headers["Access-Control-Max-Age"] = "86400"
        return resp
    # 正常业务请求走后续流程
    response: Response = await call_next(request)
    if origin and origin in allow_list:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS,PUT,DELETE"
        response.headers["Access-Control-Allow-Headers"] = "*"
        response.headers["Access-Control-Max-Age"] = "86400"
    return response

# 移除多余重复@app.options路由，避免冲突

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

# ========== 文本对话接口【完全原样，无任何修改】 ==========
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

# ========== 图片识图接口【完全原样，无任何修改】 ==========
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
