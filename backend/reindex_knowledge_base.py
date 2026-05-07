"""
重建知识库向量索引脚本。
用法：
    python reindex_knowledge_base.py          # 完整重建（删除旧数据，从原始文件重新解析）
    python reindex_knowledge_base.py --fast   # 快速重建（只重新生成向量，不改 chunks）

--fast 模式：修复 embedding 模型后使用，无需重新分块，速度快。
完整模式：更换分块策略后使用，会删除旧数据重新解析。
"""
import sys
import os
import json
import sqlite3
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from pathlib import Path

# 清除 embedding 缓存，确保获取正确维度
import services.embedding_service as embedding_service
embedding_service._dim_cache = None

from services.vector_store import DB_PATH, _get_embedding_fallback, _upsert_vector, vector_store
from services.document_parser import parse_file, chunk_text

KB_ARCHIVE_DIR = Path(__file__).parent / "knowledge_base" / "archives"


def reindex_fast():
    """快速重建：只重新生成向量，不改变 chunks 内容。"""
    import datetime
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM chunks")
    total = cursor.fetchone()[0]
    print(f"[Fast] 重新生成 {total} 个向量的 embedding...")

    cursor.execute("SELECT id, content FROM chunks")
    for i, row in enumerate(cursor.fetchall()):
        chunk_id = row["id"]
        embedding = _get_embedding_fallback(row["content"])
        cursor.execute("DELETE FROM vectors WHERE chunk_id = ?", (chunk_id,))
        _upsert_vector(cursor, chunk_id, embedding)
        if (i + 1) % 10 == 0:
            print(f"  进度: {i + 1}/{total}")
    conn.commit()
    conn.close()
    print(f"[Fast] 完成！已重新生成 {total} 个向量。")


def reindex_full():
    """完整重建：从原始文件重新解析并语义分块。"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 获取所有文档的原始路径
    cursor.execute("SELECT id, name, original_path FROM documents")
    docs = cursor.fetchall()
    if not docs:
        print("[Full] 知识库为空，无需重建。")
        return

    print(f"[Full] 找到 {len(docs)} 个文档，开始完整重建...")

    # 删除旧数据
    cursor.execute("DELETE FROM vectors")
    cursor.execute("DELETE FROM chunks")
    cursor.execute("DELETE FROM documents")
    conn.commit()
    print("[Full] 已清空旧数据")

    # 重新入库
    import datetime
    for doc_row in docs:
        doc_id = doc_row["id"]
        doc_name = doc_row["name"]
        original_path = doc_row["original_path"]

        if not original_path or not os.path.exists(original_path):
            print(f"  跳过: {doc_name} (原始文件不存在: {original_path})")
            continue

        print(f"  解析: {doc_name}")
        text = parse_file(original_path, doc_name)
        if not text or len(text.strip()) < 10:
            print(f"    解析失败，跳过")
            continue

        chunks = chunk_text(text)
        print(f"    分块: {len(chunks)} 个")

        created_at = datetime.datetime.now().isoformat()
        cursor.execute(
            "INSERT INTO documents (id, name, file_type, created_at, chunk_count, original_path) VALUES (?, ?, ?, ?, ?, ?)",
            (doc_id, doc_name, Path(doc_name).suffix.lstrip("."), created_at, len(chunks), original_path)
        )

        for idx, chunk_text_content in enumerate(chunks):
            import uuid
            chunk_id = str(uuid.uuid4())
            cursor.execute(
                "INSERT INTO chunks (id, doc_id, chunk_index, content, created_at) VALUES (?, ?, ?, ?, ?)",
                (chunk_id, doc_id, idx, chunk_text_content, created_at)
            )
            embedding = _get_embedding_fallback(chunk_text_content)
            _upsert_vector(cursor, chunk_id, embedding)

        conn.commit()
        print(f"    完成: {doc_name}")

    conn.close()
    print("[Full] 完整重建完成！")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fast", action="store_true", help="快速重建：只重新生成向量")
    args = parser.parse_args()

    if args.fast:
        reindex_fast()
    else:
        reindex_full()
