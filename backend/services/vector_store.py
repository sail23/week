"""
向量存储服务 — 基于 sqlite-vec 的 SQLite 向量数据库 + BM25 混合检索。
支持增删查操作，自动初始化表结构。
"""
import sqlite3
import json
import uuid
import re
from pathlib import Path
from typing import List, Tuple, Dict, Optional

KB_DIR = Path(__file__).resolve().parent.parent / "knowledge_base"
KB_DIR.mkdir(exist_ok=True)
DB_PATH = KB_DIR / "vectors.db"


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    _init_schema(conn)
    return conn


def _get_embedding_dim() -> int:
    try:
        from services.embedding_service import get_embedding_dim
        return get_embedding_dim()
    except Exception:
        return 1024


def _init_schema(conn: sqlite3.Connection):
    """初始化表结构（如果不存在）。"""
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            file_type TEXT NOT NULL,
            created_at TEXT NOT NULL,
            chunk_count INTEGER DEFAULT 0,
            original_path TEXT DEFAULT ''
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            id TEXT PRIMARY KEY,
            doc_id TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            content TEXT NOT NULL,
            metadata TEXT DEFAULT '{}',
            created_at TEXT NOT NULL,
            FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON chunks(doc_id)
    """)

    try:
        import sqlite_vec
        cursor.execute("SELECT sqlite_vec_version()")
        vec_version = cursor.fetchone()[0]
        print(f"[VectorStore] sqlite-vec {vec_version} loaded successfully")

        actual_dim = _get_embedding_dim()
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS vectors USING vec0(
                chunk_id TEXT,
                embedding FLOAT[%s]
            )
        """ % actual_dim)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_vectors_chunk_id ON vectors(chunk_id)
        """)

    except ImportError:
        print("[VectorStore] sqlite-vec not available, using fallback mode")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vectors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chunk_id TEXT NOT NULL,
                embedding TEXT NOT NULL,
                UNIQUE(chunk_id)
            )
        """)

    conn.commit()


def _tokenize_chinese(text: str) -> List[str]:
    """中文分词，使用 jieba 精确分词替代 n-gram 滑动窗口。"""
    import jieba
    tokens = []
    for word in jieba.cut(text):
        word = word.strip()
        if not word:
            continue
        # 保留中文词和英文/数字词，过滤纯标点
        if re.search(r"[一-鿿]", word) or re.search(r"[a-zA-Z0-9]", word):
            tokens.append(word)
    return tokens


class BM25Store:
    """BM25 倒排索引封装，支持增量增删。"""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.corpus: List[str] = []
        self.chunk_ids: List[str] = []
        self.model: Optional[object] = None
        self._load_from_db()

    def _load_from_db(self):
        """从数据库加载所有 chunks，构建 BM25 索引。"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, content FROM chunks ORDER BY chunk_index")
        rows = cursor.fetchall()
        for row in rows:
            self.chunk_ids.append(row[0])
            self.corpus.append(row[1])

        if self.corpus:
            from rank_bm25 import BM25Okapi
            tokenized = [self._tokenize(doc) for doc in self.corpus]
            self.model = BM25Okapi(tokenized)

    def _tokenize(self, text: str) -> List[str]:
        return _tokenize_chinese(text)

    def add_doc(self, chunk_id: str, content: str):
        """追加单个文档到 BM25 索引。"""
        self.chunk_ids.append(chunk_id)
        self.corpus.append(content)
        if self.model is not None:
            self.model.add(self._tokenize(content))

    def remove_doc(self, chunk_id: str):
        """从 BM25 索引中移除文档（通过重建）。"""
        if chunk_id in self.chunk_ids:
            idx = self.chunk_ids.index(chunk_id)
            self.chunk_ids.pop(idx)
            self.corpus.pop(idx)
            self._rebuild()

    def _rebuild(self):
        """重建 BM25 模型。"""
        if self.corpus:
            from rank_bm25 import BM25Okapi
            tokenized = [self._tokenize(doc) for doc in self.corpus]
            self.model = BM25Okapi(tokenized)
        else:
            self.model = None

    def search(self, query: str, top_k: int) -> Dict[str, float]:
        """
        BM25 检索。
        返回 {chunk_id: 归一化BM25分数}，归一化到 [0, 1]。
        """
        if not self.model or not self.corpus:
            return {}

        tokenized_query = self._tokenize(query)
        scores = self.model.get_scores(tokenized_query)

        # 归一化到 [0, 1]
        max_score = max(scores) if max(scores) > 0 else 1.0
        return {self.chunk_ids[i]: s / max_score for i, s in enumerate(scores) if s > 0}


class VectorStore:
    """向量存储封装，同时管理 SQLite 向量索引和 BM25 索引。"""

    def __init__(self):
        self._conn = _get_conn()
        self.bm25_store = BM25Store(self._conn)

    def add_document(self, name: str, file_type: str, chunks: List[str], original_path: str = "") -> str:
        """新增文档，自动分块并写入向量。返回 doc_id。"""
        doc_id = str(uuid.uuid4())
        import datetime
        created_at = datetime.datetime.now().isoformat()

        cursor = self._conn.cursor()
        cursor.execute(
            "INSERT INTO documents (id, name, file_type, created_at, chunk_count, original_path) VALUES (?, ?, ?, ?, ?, ?)",
            (doc_id, name, file_type, created_at, len(chunks), original_path)
        )

        for idx, chunk_text in enumerate(chunks):
            chunk_id = str(uuid.uuid4())
            cursor.execute(
                "INSERT INTO chunks (id, doc_id, chunk_index, content, created_at) VALUES (?, ?, ?, ?, ?)",
                (chunk_id, doc_id, idx, chunk_text, created_at)
            )
            embedding = _get_embedding_fallback(chunk_text)
            _upsert_vector(cursor, chunk_id, embedding)
            self.bm25_store.add_doc(chunk_id, chunk_text)

        self._conn.commit()
        return doc_id

    def delete_document(self, doc_id: str):
        """删除文档及其所有块和向量。"""
        cursor = self._conn.cursor()
        cursor.execute("SELECT id FROM chunks WHERE doc_id = ?", (doc_id,))
        chunk_ids = [row[0] for row in cursor.fetchall()]
        for chunk_id in chunk_ids:
            _delete_vector_fallback(cursor, chunk_id)
            self.bm25_store.remove_doc(chunk_id)
        cursor.execute("DELETE FROM chunks WHERE doc_id = ?", (doc_id,))
        cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        self._conn.commit()

    def _vector_search(self, query: str, top_k: int) -> List[Tuple[str, str, float]]:
        """纯向量检索，返回 List[(chunk_id, content, cosine_score)]。"""
        query_embedding = _get_embedding_fallback(query)
        cursor = self._conn.cursor()

        try:
            import sqlite_vec
            cursor.execute("""
                SELECT v.chunk_id, c.content, v.embedding
                FROM vectors v
                JOIN chunks c ON c.id = v.chunk_id
            """)
            rows = cursor.fetchall()
        except (ImportError, Exception):
            cursor.execute("""
                SELECT v.chunk_id, c.content, v.embedding
                FROM vectors v
                JOIN chunks c ON c.id = v.chunk_id
            """)
            rows = cursor.fetchall()

        scored = []
        for row in rows:
            chunk_id = row[0]
            content = row[1]
            vec_str = row[2]
            stored_vec = json.loads(vec_str) if isinstance(vec_str, str) else vec_str
            score = _cosine_similarity(query_embedding, stored_vec)
            scored.append((chunk_id, content, score))

        scored.sort(key=lambda x: x[2], reverse=True)
        return scored[:top_k]

    MIN_COSINE_SIMILARITY = 0.30

    def search(self, query: str, top_k: int = 5, alpha: float = 0.2, rrf_k: int = 40) -> List[Tuple[str, str, float]]:
        """
        混合检索：向量 + BM25 Reciprocal Rank Fusion (RRF)。

        RRF 融合公式：score = sum(weight / (k + rank))。
        k=40：更平滑的排名衰减，减少极端排名差异。
        alpha=0.2：向量权重 80%，BM25 权重 20%。以向量语义匹配为主，
        BM25 仅作为关键词命中的辅助信号，避免 n-gram 噪声主导排序。
        alpha=0.0 表示纯向量，alpha=1.0 表示纯 BM25。
        """
        # 1. 向量检索（取更多候选）
        vec_results = self._vector_search(query, top_k * 3)

        # 硬性过滤：余弦相似度低于阈值的 chunk 不参与 RRF 融合
        vec_results = [(cid, content, s) for cid, content, s in vec_results if s >= self.MIN_COSINE_SIMILARITY]

        # 2. BM25 检索
        bm25_scores: Dict[str, float] = self.bm25_store.search(query, top_k * 3)

        max_cosine = max((s for _, _, s in vec_results), default=0.0)
        if max_cosine < 0.35 and bm25_scores:
            alpha = max(0.0, alpha - 0.3)

        # 3. 构建 RRF 融合分
        fused: Dict[str, float] = {}
        for rank, (cid, _, cosine_s) in enumerate(vec_results):
            weight = 1.0 - alpha
            fused[cid] = fused.get(cid, 0.0) + weight / (rrf_k + rank + 1)

        # 如果最大 BM25 分数接近零，减小其权重
        max_bm25 = max(bm25_scores.values(), default=0.0)
        bm25_weight = alpha if max_bm25 > 0.01 else 0.0
        for rank, (cid, bm25_s) in enumerate(
            sorted(bm25_scores.items(), key=lambda x: x[1], reverse=True)
        ):
            fused[cid] = fused.get(cid, 0.0) + bm25_weight / (rrf_k + rank + 1)

        # 4. 按融合分排序，补充 content
        cursor = self._conn.cursor()
        sorted_ids = sorted(fused.keys(), key=lambda c: fused[c], reverse=True)

        max_fused = fused[sorted_ids[0]] if sorted_ids else 0.0

        results = []
        for cid in sorted_ids[:top_k]:
            cursor.execute("SELECT content FROM chunks WHERE id = ?", (cid,))
            row = cursor.fetchone()
            if row:
                results.append((cid, row[0], fused[cid]))

        # 用 max_cosine 做参考缩放，保留真实相关性信号
        if results and max_fused > 0:
            scale = max_cosine * 200
            results = [
                (cid, content, round((score / max_fused) * scale, 1))
                for cid, content, score in results
            ]

        return results

    def list_documents(self) -> List[dict]:
        """列出所有文档。"""
        cursor = self._conn.cursor()
        cursor.execute("SELECT id, name, file_type, created_at, chunk_count FROM documents ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]

    def get_stats(self) -> dict:
        """返回知识库统计信息。"""
        cursor = self._conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM documents")
        doc_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM chunks")
        chunk_count = cursor.fetchone()[0]
        return {"doc_count": doc_count, "chunk_count": chunk_count}

    def close(self):
        self._conn.close()


def _get_embedding_fallback(text: str) -> List[float]:
    try:
        from services.embedding_service import get_embedding
        return get_embedding(text)
    except Exception:
        dim = _get_embedding_dim()
        return [0.0] * dim


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _upsert_vector(cursor, chunk_id: str, embedding: List[float]):
    vec_json = json.dumps(embedding)
    try:
        import sqlite_vec
        cursor.execute("INSERT OR REPLACE INTO vectors (chunk_id, embedding) VALUES (?, ?)",
                       (chunk_id, embedding))
    except (ImportError, Exception):
        cursor.execute("INSERT OR REPLACE INTO vectors (chunk_id, embedding) VALUES (?, ?)",
                       (chunk_id, vec_json))


def _delete_vector_fallback(cursor, chunk_id: str):
    try:
        import sqlite_vec
        cursor.execute("DELETE FROM vectors WHERE chunk_id = ?", (chunk_id,))
    except (ImportError, Exception):
        cursor.execute("DELETE FROM vectors WHERE chunk_id = ?", (chunk_id,))


vector_store = VectorStore()
