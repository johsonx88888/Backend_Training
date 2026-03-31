# RAG 知识库模块
import chromadb

# ChromaDB 客户端配置（新版 API）
chroma_client = chromadb.PersistentClient(
    path="./chroma_db"  # 数据保存目录
)

# 获取或创建集合（类似数据库的表）
collection = chroma_client.get_or_create_collection(name="knowledge")


def add_document(doc_id: str, content: str):
    """
    添加文档到知识库
    
    参数:
        doc_id: 文档唯一标识（如"doc_001"）
        content: 文档内容
    """
    collection.add(
        ids=[doc_id],
        documents=[content]
    )


def search_documents(query: str, n_results: int = 3):
    """
    搜索相关文档
    
    参数:
        query: 用户问题
        n_results: 返回最相关的几条
    
    返回:
        相关文档列表
    """
    results = collection.query(
        query_texts=[query],
        n_results=n_results
    )
    return results["documents"][0] if results["documents"] else []


def init_rag_data():
    """初始化一些示例数据"""
    # 添加几条示例文档
    sample_docs = [
        ("doc_001", "公司年假规定：员工入职满1年可享受10天带薪年假，满5年享受15天。"),
        ("doc_002", "加班制度：工作日加班按1.5倍工资计算，周末按2倍，节假日按3倍。"),
        ("doc_003", "请假流程：请提前3天在OA系统提交申请，经直属领导审批后方可休假。"),
    ]
    
    for doc_id, content in sample_docs:
        add_document(doc_id, content)


if __name__ == "__main__":
    # 测试：初始化数据并搜索
    init_rag_data()
    
    # 测试搜索
    query = "年假有几天？"
    results = search_documents(query)
    print(f"问题：{query}")
    print(f"相关文档：{results}")
