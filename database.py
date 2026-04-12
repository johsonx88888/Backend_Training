#数据库操作块
import aiosqlite
import traceback
from openai import OpenAI
import os

# 加载环境变量（确保能读到 API Key）
from dotenv import load_dotenv
load_dotenv()

DATABASE="chat.db"  #数据库文件名

# AI 客户端（用来调用大模型筛选短期记忆中的重要信息作为长期存储）
extract_client = OpenAI(
    api_key=os.getenv("SILICONFLOW_API_KEY"),
    base_url="https://api.siliconflow.cn/v1"
)

# 存对话内容（短期记忆）
# 结构： user_id: { session_id: [ {role, content}, ... ] } }
memory_store = {}


# 计数器：只记录本轮对话发了多少条（和短期记忆分开）
message_counter = {}


def get_message_count(user_id: str, session_id: str) -> int:
    """获取当前会话的消息数量"""
    key = f"{user_id}:{session_id}"
    return message_counter.get(key, 0)

def increment_message_count(user_id: str, session_id: str) -> int:
    """消息数量 +1，返回当前数量"""
    key = f"{user_id}:{session_id}"
    current = message_counter.get(key, 0)  # 获取，不修改
    message_counter[key] = current + 1      # 修改，存新值
    return message_counter[key]          # 返回新值

def reset_message_count(user_id: str, session_id: str):
    """重置计数器（筛选完长期记忆后调用）"""
    key = f"{user_id}:{session_id}"
    if key in message_counter:
        del message_counter[key] 

# 获取长期记忆
async def get_long_term_memory(user_id: str, session_id: str) -> list:
    """获取某个用户的某个会话的长期记忆"""
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute(
            "SELECT memory_content FROM long_term_memories WHERE user_id=? AND session_id=? ORDER BY id DESC",
            (user_id, session_id)
        ) as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]  # 只返回内容列表

#ai 客户端提取重要信息存入长期记忆
async def extract_and_save_long_term_memory(user_id: str, session_id: str):
    """用 AI 分析最近10条消息，提取重要信息存入长期记忆"""
    try:
        #1、获取近10条聊天记录
        history=await get_history(user_id, session_id, limit=10)
        
        if not history:
            print(f"[长期记忆] 没有历史记录，跳过提取")
            return
        
        #2、拼接成文本
        conversation="\n".join([
            f"{msg['role']}: {msg['content']}"
            for msg in reversed(history)
        ])

        #3、让AI提取重要信息
        prompt=f"""请分析一下对话，提取需要长期记住的重要信息（如用户的喜好、重要事实、约定等）如果没有什么重要信息，请回复"无"。
    对话内容：
    {conversation}

    请用简洁单独一句话总结每条重要信息,每行一条：
    """
        print(f"[长期记忆] 调用AI提取，历史记录数: {len(history)}")
        
        response=extract_client.chat.completions.create(
            model="Qwen/Qwen2.5-7B-Instruct",
            messages=[{"role":"user","content":prompt}],
            stream=False,
        )
        result=response.choices[0].message.content.strip()
        print(f"[长期记忆] AI返回: {result}")

        #4、如果有重要信息，存入长期记忆
        if result and result !="无":
            count = 0
            for memory in result.split("\n"):  #分行读取
                memory=memory.strip()
                if memory:
                    await save_long_term_memory(user_id, session_id, memory)
                    count += 1
            print(f"[长期记忆] 成功保存 {count} 条")
        else:
            print(f"[长期记忆] AI认为没有重要信息")
    except Exception as e:
        print(f"[长期记忆] 提取失败: {e}")
       
        traceback.print_exc()

# 长期记忆存储（数据库表里加一个）
async def save_long_term_memory(user_id: str, session_id: str, memory_content: str):
    """保存长期记忆到数据库"""
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute(
            "INSERT INTO long_term_memories(user_id, session_id, memory_content) VALUES(?,?,?)",
            (user_id, session_id, memory_content)
        )
        await db.commit()

def get_hisory_from_memory(user_id:str,session_id:str)->list:
    """从内存里拿某个用户的某个会话记录"""  #(短期字典记忆)
    return memory_store.get(user_id,{}).get(session_id,[])

def append_to_memory(user_id:str,session_id:str,role:str,content:str):
    """把用户问题或AI回复存入内存"""
    if user_id not in memory_store:
        memory_store[user_id] = {}   #没有用户的存储区就先建一个空的存储区
    if session_id not in memory_store[user_id]:
        memory_store[user_id][session_id]=[]   #没有存储区的对话框就先建一个空的对话框
      #追加消息
    memory_store[user_id][session_id].append({"role":role,"content":content})

def clear_session(user_id:str,session_id:str):
    """清空某个会话的记忆（新建会话时用）"""
    if user_id in memory_store and session_id in memory_store[user_id]:
        del memory_store[user_id][session_id]
        return True
    return False
    
#连库建表
async def init_db():
    """初始化数据库"""
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS messages(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,      -- 新增：用户标识
        session_id TEXT NOT NULL,   -- 新增：会话标识
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        await db.execute("""
        CREATE TABLE IF NOT EXISTS long_term_memories(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        session_id TEXT NOT NULL,
        memory_content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        await db.commit()

#保存消息
async def save_message(user_id:str, session_id:str, role:str, content:str):
    """保存消息到数据库（用户隔离）"""
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute(
            "INSERT INTO messages(user_id, session_id,role,content) VALUES(?,?,?,?)",
            (user_id, session_id, role, content)
        )
        await db.commit()

#获取历史消息记录
async def get_history(user_id: str, session_id: str, limit: int =20):
    """获取某个用户的某个会话的历史消息"""
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute(
           "SELECT role,content,created_at FROM messages WHERE user_id=? AND session_id=? ORDER BY id DESC LIMIT ?",
            (user_id, session_id, limit)
        ) as cursor:
           rows=await cursor.fetchall()
           return [
            {"role":row[0],"content":row[1],"time":row[2]}
            for row in rows
           ]
