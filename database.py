#数据库操作块
import aiomysql
from redis import asyncio as aioredis  # 新版 redis 的异步支持
import traceback
from openai import OpenAI
import os
from logger import logger

# 加载环境变量（确保能读到 API Key）
from dotenv import load_dotenv
load_dotenv()

# MySQL 数据库配置
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "backend_training")

# Redis 配置（新增）
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

# AI 客户端（用来调用大模型筛选短期记忆中的重要信息作为长期存储）
extract_client = OpenAI(
    api_key=os.getenv("SILICONFLOW_API_KEY"),
    base_url="https://api.siliconflow.cn/v1"
)

# 存对话内容（短期记忆）
# 结构： user_id: { session_id: [ {role, content}, ... ] } }
memory_store = {}

# 建立Redis连接池
redis_pool=None

async def get_redis():
    """获取Redis连接"""
    global redis_pool
    if redis_pool is None:
        redis_pool=aioredis.from_url(
            f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}",
            encoding="utf-8",
            decode_responses=True
        )
    return redis_pool


# 缓存相关函数

# 获取缓存数据
async def get_from_cache(key:str):
    """从缓存获取数据"""
    try:
        redis=await get_redis()
        data=await redis.get(key)
        return data
    except Exception as e:
        logger.warning("缓存读取失败: %s", e)
        return None

# 添加缓存并设置有效时间
async def set_cache(key:str,value:str,expire:int=3600):
    """设置缓存，默认1小时过期"""
    try:
        redis=await get_redis()   # 连接缓存
        await redis.set(key,value,ex=expire) # 添加缓存
        logger.info("缓存已设置: %s", key)
    except Exception as e:
        logger.warning("缓存设置失败: %s", e)
        return False

# 删除缓存
async def delete_cache(key:str):
    """删除缓存"""
    try:
        redis=await get_redis()
        await redis.delete(key)
    except Exception as e:
        logger.warning("缓存删除失败: %s", e)

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
    conn = await aiomysql.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, db=DB_NAME)
    async with conn.cursor() as cursor:
        await cursor.execute(
            "SELECT memory_content FROM long_term_memories WHERE user_id=%s AND session_id=%s ORDER BY id DESC",
            (user_id, session_id)
        )
        rows = await cursor.fetchall()
        conn.close()
        return [row[0] for row in rows]  # 只返回内容列表

#ai 客户端提取重要信息存入长期记忆
async def extract_and_save_long_term_memory(user_id: str, session_id: str):
    """用 AI 分析最近10条消息，提取重要信息存入长期记忆"""
    try:
        #1、获取近10条聊天记录
        history=await get_history(user_id, session_id, limit=10)
        
        if not history:
            logger.info("长期记忆: 没有历史记录，跳过提取")
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
        logger.info("长期记忆: 调用AI提取，历史记录数: %s", len(history))
        
        response=extract_client.chat.completions.create(
            model="Qwen/Qwen2.5-7B-Instruct",
            messages=[{"role":"user","content":prompt}],
            stream=False,
        )
        result=response.choices[0].message.content.strip()
        logger.debug("长期记忆: AI返回: %s", result)

        #4、如果有重要信息，存入长期记忆
        if result and result !="无":
            count = 0
            for memory in result.split("\n"):  #分行读取
                memory=memory.strip()
                if memory:
                    await save_long_term_memory(user_id, session_id, memory)
                    count += 1
            logger.info("长期记忆: 成功保存 %s 条", count)
        else:
            logger.info("长期记忆: AI认为没有重要信息")
    except Exception as e:
        logger.error("长期记忆: 提取失败: %s", e)
       
        traceback.print_exc()

# 长期记忆存储（数据库表里加一个）
async def save_long_term_memory(user_id: str, session_id: str, memory_content: str):
    """保存长期记忆到数据库"""
    conn = await aiomysql.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, db=DB_NAME)
    async with conn.cursor() as cursor:
        await cursor.execute(
            "INSERT INTO long_term_memories(user_id, session_id, memory_content) VALUES(%s,%s,%s)",
            (user_id, session_id, memory_content)
        )
        await conn.commit()
    conn.close()

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

async def clear_session(user_id:str,session_id:str):
    """清空某个会话的记忆和数据库记录"""
    #1、删除内存中的短期记忆
    if user_id in memory_store and session_id in memory_store[user_id]:
        del memory_store[user_id][session_id]
    
    #2、删除数据库中的记录
    conn = await aiomysql.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, db=DB_NAME)
    async with conn.cursor() as cursor:
        await cursor.execute(
            "DELETE FROM messages WHERE user_id=%s AND session_id=%s",
            (user_id, session_id)
        )
        await conn.commit()
    conn.close()
    
    #3、删除Redis缓存
    cache_key = f"history:{user_id}:{session_id}"
    await delete_cache(cache_key)
    
    return True
    
#连库建表
async def init_db():
    """初始化数据库"""
    conn = await aiomysql.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, db=DB_NAME)
    async with conn.cursor() as cursor:
        # 消息表
        await cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages(
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id VARCHAR(255) NOT NULL,
        session_id VARCHAR(255) NOT NULL,
        role VARCHAR(50) NOT NULL,
        content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        #长期记忆表
        await cursor.execute("""
        CREATE TABLE IF NOT EXISTS long_term_memories(
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id VARCHAR(255) NOT NULL,
        session_id VARCHAR(255) NOT NULL,
        memory_content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        #用户表（存用户积分信息）
        await cursor.execute("""
        CREATE TABLE IF NOT EXISTS users(
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id VARCHAR(255) UNIQUE NOT NULL,
        credits INT DEFAULT 100,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        await conn.commit()
    conn.close()
    logger.info("数据库初始化完成")


#获取用户积分（若是新用户则创建，赠送100积分）
async def get_user_credits(user_id: str) -> int:
    """获取用户当前积分，没有则创建默认100"""
    conn=await aiomysql.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, db=DB_NAME)
    async with conn.cursor() as cursor:
        #先查有没有这个用户
        await cursor.execute("SELECT credits FROM users WHERE user_id=%s",(user_id,))
        row=await cursor.fetchone()

        if row:
            credits=row[0]
        else:
            #没有就创建，默认100积分
            await cursor.execute("INSERT INTO users(user_id,credits) VALUES(%s,100)",(user_id,))
            await conn.commit()
            credits=100
            logger.info("新用户 %s 创建，赠送100积分", user_id)
        conn.close()
        return credits

#扣除用户积分
async def deduct_credits(user_id: str, amount: int) -> bool:
    """扣除用户积分，成功返回True，失败返回False"""
    conn=await aiomysql.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, db=DB_NAME)
    async with conn.cursor() as cursor:
        #1、先查用户当前积分
        await cursor.execute("SELECT credits FROM users WHERE user_id=%s",(user_id,))
        row=await cursor.fetchone()

        if not row:
            conn.close()
            logger.warning("用户 %s 不存在", user_id)
            return False   #用户不存在
        
        current=row[0]
        if current<amount:
            conn.close()
            logger.warning("用户 %s 积分不足 %s，当前积分 %s", user_id, amount, current)
            return False    #积分不够

        #2、扣积分
        new_credits=current-amount
        await cursor.execute("UPDATE users SET credits=%s WHERE user_id=%s",(new_credits,user_id))
        await conn.commit()
        conn.close()
        logger.info("用户 %s 扣除 %s 积分，剩余 %s 积分", user_id, amount, new_credits)
        return True


#增加用户积分
async def add_credits(user_id: str, amount: int) -> int:
    """给用户增加积分，返回增加后的总积分"""
    conn = await aiomysql.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, db=DB_NAME)
    async with conn.cursor() as cursor:
        #1、查当前积分
        await cursor.execute("SELECT credits FROM users WHERE user_id=%s", (user_id,))
        result = await cursor.fetchone()

        if result:
            current = result[0]
            new_credits = current + amount
            await cursor.execute("UPDATE users SET credits=%s WHERE user_id=%s", (new_credits, user_id))
        else:
            # 用户不存在，先创建（给100）再加
            new_credits = 100 + amount
            await cursor.execute("INSERT INTO users (user_id, credits) VALUES (%s, %s)", (user_id, new_credits))
        await conn.commit()
        conn.close()
        logger.info("用户 %s 增加 %s 积分，当前 %s 积分", user_id, amount, new_credits)
        return new_credits


#保存消息
async def save_message(user_id:str, session_id:str, role:str, content:str):
    """保存消息到数据库（用户隔离）"""
    conn = await aiomysql.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, db=DB_NAME)
    async with conn.cursor() as cursor:
        await cursor.execute(
            "INSERT INTO messages(user_id, session_id,role,content) VALUES(%s,%s,%s,%s)",
            (user_id, session_id, role, content)
        )
        await conn.commit()
    conn.close()

#获取历史消息记录
async def get_history(user_id: str, session_id: str, limit: int =20):
    """获取某个用户的某个会话的历史消息"""
    conn = await aiomysql.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, db=DB_NAME)
    async with conn.cursor() as cursor:
        await cursor.execute(
           "SELECT role,content,created_at FROM messages WHERE user_id=%s AND session_id=%s ORDER BY id DESC LIMIT %s",
            (user_id, session_id, limit)
        )
        rows=await cursor.fetchall()
        conn.close()
        return [
            {"role":row[0],"content":row[1],"time":row[2].strftime("%Y-%m-%d %H:%M:%S") if row[2] else None}
            for row in rows
        ]
