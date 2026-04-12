from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
import os
from dotenv import load_dotenv as load_env_file
from fastapi.responses import StreamingResponse
from database import (
    init_db, save_message, get_history,
    get_hisory_from_memory, append_to_memory, clear_session,
    save_long_term_memory, get_long_term_memory,  # 新增：读长期记忆
    extract_and_save_long_term_memory,             # 新增：AI筛选
    increment_message_count, reset_message_count   # 新增：计数器
)
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
    user_id:str
    session_id:str

@app.on_event("startup")
async def startup():
    """服务启动时初始化数据库和RAG知识库"""
    await init_db()
    init_rag_data()  # 初始化示例知识库

@app.get("/history")
async def history(user_id:str,session_id:str,limit:int =20):
    """获取历史消息"""
    messages = await get_history(user_id, session_id, limit)
    return {"messages": messages}

@app.delete("/chat/session")
async def clear_chat_session(user_id:str,session_id:str):
    """清空聊天会话"""
    success=clear_session(user_id,session_id)
    if success:
        return {"message":f"会话{session_id}已清空"}
    else:
        return {"message":f"会话{session_id}不存在"}

@app.get("/")
def root():
    return{"message": "欢迎来到此网页"}


@app.get("/hello")
def hello():
    return "hello world"

@app.post("/chat")
async def chat(request: ChatRequest):
    """与 AI 对话（流式输出）,支持记忆功能"""
    # 先保存用户消息，把用户问题存入记忆
    append_to_memory(request.user_id,request.session_id,"user",request.message)
    
    # 返回流式响应
    return StreamingResponse(
        generate_ai_response(request.user_id,request.session_id,request.message),
        media_type="text/plain"  # 纯文本流式输出
    )


async def generate_ai_response(user_id: str, session_id: str, message: str):
    """流式生成 AI 回复，带RAG检索和异常处理"""
    # 先把用户消息存了（不管AI是否成功，用户消息都要记录）
    append_to_memory(user_id, session_id, "user", message)
    await save_message(user_id, session_id, "user", message)
    
    try:
        # Step 1:先读短期记忆
        history=get_hisory_from_memory(user_id,session_id)
        #Step 1.5：再读长期记忆
        long_memories=await get_long_term_memory(user_id,session_id)
        if long_memories:
            memory_context="以下是你之前记住的重要信息：\n" + "\n".join(long_memories)
            history.insert(0, {"role": "system", "content": memory_context})

        #Step 2: RAG检索 - 先查相关知识库
        relevant_docs = search_documents(message, n_results=2)
        context = "\n".join(relevant_docs) if relevant_docs else ""
        
        # Step 3: 构建历史消息（历史+rag检索+新问题）
        messages=history.copy() #1、先放历史记录
        
        #2、如果有rag，加一条系统提示
        if context:
            messages.append({
                "role":"system",
                "content":f"参考资料：{context}\n请根据以上资料回答，如果资料中没有相关信息，请说明。"
            })
        
        #3、最后加用户新问题
        messages.append({
            "role":"user",
            "content":message
        })
        
        # Step 4: 调用 AI，开启流式输出
        response = ai_client.chat.completions.create(
            model="Qwen/Qwen2.5-7B-Instruct",
            messages=messages,
            stream=True  # 开启流式
        )
        
        full_reply = ""
        for chunk in response:
            # 获取当前片段的内容
            content = chunk.choices[0].delta.content
            if content:
                full_reply += content
                yield content  # 逐字返回给前端
        
        # 流式输出完成后 ← 存到记忆字典里（短期记忆）
        append_to_memory(user_id, session_id, "assistant", full_reply)  
        # 同时存到数据库（长期存档，管理员用）
        await save_message(user_id, session_id, "assistant", full_reply)
        
    except Exception as e:
        # 硅基流动错误码对照处理，用户无需查文档
        error_msg = str(e)
        print(f"[AI错误] {error_msg}")  # 打印具体错误
        
        if "30001" in error_msg or "balance is insufficient" in error_msg:
            yield "【错误】账户余额不足，请充值或联系管理员"
        elif "30002" in error_msg or "Invalid API Key" in error_msg:
            yield "【错误】API 密钥无效，请检查 .env 文件配置"
        elif "30003" in error_msg:
            yield "【错误】请求参数错误，请检查输入内容"
        elif "30004" in error_msg:
            yield "【错误】模型不存在或不可用，请检查模型名称"
        elif "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
            yield "【错误】请求超时，请稍后再试"
        elif "connection" in error_msg.lower():
            yield "【错误】网络连接异常，请检查网络设置"
        else:
            yield f"【错误】AI 服务异常，请稍后再试或联系管理员"
        
        # 即使AI失败，也要继续执行计数器逻辑
        full_reply = ""
    
    # 计数器逻辑（不管AI是否成功，都要执行）
    count=increment_message_count(user_id,session_id)
    if count>=10:
        #满了，触发AI筛选重要信息并存到长期记忆里去
        await extract_and_save_long_term_memory(user_id, session_id)
        #重置计数器
        reset_message_count(user_id, session_id)
        yield "【提示】已将会话内容中重要信息提取并保存到长期记忆中，以节省短期记忆空间。"
