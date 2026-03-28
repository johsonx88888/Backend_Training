from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
import os
from dotenv import load_dotenv as load_env_file

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

@app.get("/")
def root():
    return{"message": "欢迎来到此网页"}


@app.get("/hello")
def hello():
    return "hello world"


@app.post("/chat")
def chat(request: ChatRequest):
    """与 AI 对话"""
    response = ai_client.chat.completions.create(
        model="deepseek-ai/DeepSeek-V3",  # 或其他模型
        messages=[
            {"role": "user", "content": request.message}
        ]
    )
    return {
        "reply": response.choices[0].message.content
    }
