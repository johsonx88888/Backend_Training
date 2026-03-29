from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
import os
from dotenv import load_dotenv as load_env_file
from database import init_db,save_message,get_history

# 加载环境变量配置文件（从 .env 文件读取 API 密钥等配置）
load_env_file()

app = FastAPI()

# AI 客户端配置（连接硅基流动大模型服务）
ai_client = OpenAI(
    api_key=os.getenv("SILICONFLOW_API_KEY"),
    base_url="https://api.siliconflow.cn/v1"
)

# 数据验证
class ChatRequest(BaseModel):
    message: str

@app.on_event("startup")
async def startup():
    """服务启动时初始化数据库"""
    await init_db()

@app.get("/history")
async def history(limit:int =20):
    """获取历史消息"""
    messages = await get_history(limit)
    return {"messages": messages}

@app.get("/")
def root():
    return{"message": "欢迎来到此网页"}


@app.get("/hello")
def hello():
    return "hello world"


@app.post("/chat")
async def chat(request: ChatRequest):
    """与 AI 对话"""
    await save_message("user",request.message)
    response = ai_client.chat.completions.create(
        model="deepseek-ai/DeepSeek-V3",  # 或其他模型
        messages=[
            {"role": "user", "content": request.message}
        ]
    )
    ai_reply = response.choices[0].message.content
    await save_message("assistant", ai_reply)
    return {
        "reply": ai_reply
    }
