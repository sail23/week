"""
Embedding 服务 — 通过 OpenAI 兼容接口调用外部 embedding 模型服务。
使用 urllib 进行 HTTP 调用（stdlib，无 TLS 兼容性问题）。
"""
import json
from typing import List
from urllib.request import Request, urlopen
from urllib.error import URLError
from config import settings

_dim_cache = None


def _fetch_embedding_dim() -> int:
    global _dim_cache
    if _dim_cache is not None:
        return _dim_cache
    try:
        resp = _call_embedding_api("你好")
        _dim_cache = len(resp)
        return _dim_cache
    except Exception:
        _dim_cache = 1024
        return 1024


def _call_embedding_api(text: str) -> List[float]:
    """调用 OpenAI 兼容的 /embeddings 接口，返回 float list。"""
    base_url = settings.embedding_base_url.rstrip("/")
    if base_url.endswith("/embeddings"):
        base_url = base_url[:-len("/embeddings")]

    body = json.dumps({
        "model": settings.embedding_model,
        "input": text,
    }).encode("utf-8")

    req = Request(
        f"{base_url}/embeddings",
        data=body,
        headers={
            "Authorization": f"Bearer {settings.embedding_api_key}",
            "Content-Type": "application/json",
        },
    )
    with urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return data["data"][0]["embedding"]


def _call_embeddings_api(texts: List[str]) -> List[List[float]]:
    """批量调用 OpenAI 兼容的 /embeddings 接口。"""
    base_url = settings.embedding_base_url.rstrip("/")

    body = json.dumps({
        "model": settings.embedding_model,
        "input": texts,
    }).encode("utf-8")

    req = Request(
        f"{base_url}/embeddings",
        data=body,
        headers={
            "Authorization": f"Bearer {settings.embedding_api_key}",
            "Content-Type": "application/json",
        },
    )
    with urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return [item["embedding"] for item in data["data"]]


def get_embedding(text: str) -> List[float]:
    """对单条文本生成 embedding 向量。"""
    return _call_embedding_api(text)


def get_embeddings(texts: List[str]) -> List[List[float]]:
    """批量生成 embedding 向量。"""
    if not texts:
        return []
    return _call_embeddings_api(texts)


def get_embedding_dim() -> int:
    """返回 embedding 向量维度，由外部服务决定。"""
    return _fetch_embedding_dim()
