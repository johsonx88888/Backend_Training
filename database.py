#数据库操作块
import aiosqlite
DATABASE="chat.db"  #数据库文件名
async def init_db():
    """初始化数据库"""
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS messages(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        await db.commit()

async def save_message(role:str,content:str):
    """保存消息到数据库"""
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute(
            "INSERT INTO messages(role,content) VALUES(?,?)",
            (role,content)
        )
        await db.commit()

async def get_history(limit: int =20):
    """获取历史消息"""
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute(
           "SELECT role,content,created_at FROM messages ORDER BY id DESC LIMIT ?",
            (limit,)
        ) as cursor:
           rows=await cursor.fetchall()
           return [
            {"role":row[0],"content":row[1],"time":row[2]}
            for row in rows
           ]
