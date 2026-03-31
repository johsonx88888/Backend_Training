from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
import os
from dotenv import load_dotenv as load_env_file
from database import init_db,save_message,get_history
from fastapi.responses import StreamingResponse
from rag import search_documents, init_rag_data

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
    """服务启动时初始化数据库和RAG知识库"""
    await init_db()
    init_rag_data()  # 初始化示例知识库

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
    """与 AI 对话（流式输出）"""
    # 先保存用户消息
    await save_message("user", request.message)
    
    # 返回流式响应
    return StreamingResponse(
        generate_ai_response(request.message),
        media_type="text/plain"  # 纯文本流式输出
    )


async def generate_ai_response(message: str):
    """流式生成 AI 回复，带RAG检索和异常处理"""
    try:
        # Step 1: RAG检索 - 先查相关知识库
        relevant_docs = search_documents(message, n_results=2)
        context = "\n".join(relevant_docs) if relevant_docs else ""
        
        # Step 2: 构建带上下文的提示词
        if context:
            prompt = f"""基于以下参考资料回答问题：

参考资料：
{context}

用户问题：{message}

请根据参考资料回答，如果资料中没有相关信息，请说明。"""
        else:
            prompt = message
        
        # Step 3: 调用 AI，开启流式输出
        response = ai_client.chat.completions.create(
            model="deepseek-ai/DeepSeek-V3",
            messages=[{"role": "user", "content": prompt}],
            stream=True  # 开启流式
        )
        
        full_reply = ""
        for chunk in response:
            # 获取当前片段的内容
            content = chunk.choices[0].delta.content
            if content:
                full_reply += content
                yield content  # 逐字返回给前端
        
        # 流式输出完成后，保存完整回复到数据库
        await save_message("assistant", full_reply)
        
    except Exception as e:
        # 硅基流动错误码对照处理，用户无需查文档
        error_msg = str(e)
        
        if "30001" in error_msg or "balance is insufficient" in error_msg:
            yield "【错误】账户余额不足，请充值或联系管理员"
        elif "30002" in error_msg or "Invalid API Key" in error_msg:
            yield "【错误】API 密钥无效，请检查 .env 文件配置"
        elif "30003" in error_msg:
            yield "【错误】请求参数错误，请检查输入内容"
        elif "30004" in error_msg or "Model not found" in error_msg:
            yield "【错误】模型不存在，请更换其他模型"
        elif "429" in error_msg or "Rate limit" in error_msg:
            yield "【错误】请求太频繁，请稍后再试"
        elif "500" in error_msg:
            yield "【错误】服务器繁忙，请稍后再试"
        elif "503" in error_msg:
            yield "【错误】服务暂不可用，请稍后再试"
        else:
            yield "【错误】AI 服务异常，请稍后再试或联系管理员"


