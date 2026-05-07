"""
RAG 检索服务。
接收查询文本 → embedding → 向量检索 → 拼 context 返回。
"""
from typing import List

from services.vector_store import vector_store

DEFAULT_TOP_K = 5
MIN_SCORE = 20.0


def retrieve_context(query: str, top_k: int = DEFAULT_TOP_K) -> str:
    """
    检索最相关的知识库片段，拼接为 context 字符串返回。
    如果没有检索结果或所有结果分数低于阈值，返回空字符串。
    """
    if not query or not query.strip():
        return ""

    try:
        results = vector_store.search(query, top_k=top_k)
        if not results:
            return ""

        chunks = []
        for chunk_id, content, score in results:
            if score >= MIN_SCORE:
                chunks.append(content)

        if not chunks:
            return ""

        return "[参考知识库内容]\n" + "\n\n---\n\n".join(chunks)

    except Exception:
        return ""


def retrieve_chunks(query: str, top_k: int = DEFAULT_TOP_K) -> List[dict]:
    """
    返回原始检索结果（用于调试或展示来源）。
    返回 List[dict]，每个 dict 含 chunk_id, content, score, rank。
    rank 从 1 开始，分数越高排名越靠前。
    分数低于 MIN_SCORE 的结果会被过滤。
    """
    try:
        results = vector_store.search(query, top_k=top_k)
        if not results:
            return []

        filtered = [(sid, content, score) for sid, content, score in results if score >= MIN_SCORE]
        if not filtered:
            return []

        return [
            {
                "chunk_id": sid,
                "content": content,
                "score": float(score),
                "rank": idx + 1,
                "percent": round(float(score)),
            }
            for idx, (sid, content, score) in enumerate(filtered)
        ]
    except Exception:
        return []
