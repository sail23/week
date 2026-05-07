"""
知识库管理路由。
支持文档上传、列表查看、删除、状态查询。
"""
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import Optional
import tempfile
import os
import shutil

from services.vector_store import vector_store
from services.document_parser import parse_file, chunk_text
from services.rag_service import retrieve_context, retrieve_chunks

router = APIRouter()

ALLOWED_EXTENSIONS = {".txt", ".docx", ".doc", ".pdf"}
KB_UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "knowledge_base", "uploads")
KB_ARCHIVE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "knowledge_base", "archives")
os.makedirs(KB_UPLOAD_DIR, exist_ok=True)
os.makedirs(KB_ARCHIVE_DIR, exist_ok=True)


class SearchRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5


class SearchResponse(BaseModel):
    query: str
    results: list


@router.post("/kb/upload")
async def upload_document(file: UploadFile = File(...)):
    """上传文档，解析文本，切块，生成 embedding 入库。"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名为空")

    suffix = os.path.splitext(file.filename)[1].lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型，仅支持: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # 用 doc_id 作为文件名永久保存，方便日后重建索引
    import uuid as _uuid
    doc_id = _uuid.uuid4().hex
    archive_name = f"{doc_id}_{file.filename}"
    archive_path = os.path.join(KB_ARCHIVE_DIR, archive_name)
    try:
        with open(archive_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        text = parse_file(archive_path, file.filename)
        if not text or len(text.strip()) < 10:
            raise HTTPException(status_code=422, detail="文档内容提取失败，请确保文件非空且包含可读文本")

        chunks = chunk_text(text)
        real_doc_id = vector_store.add_document(
            name=file.filename,
            file_type=suffix.lstrip("."),
            chunks=chunks,
            original_path=archive_path,
        )

        return {
            "doc_id": real_doc_id,
            "name": file.filename,
            "chunk_count": len(chunks),
            "message": f"上传成功，已解析 {len(chunks)} 个文本块"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")


@router.get("/kb/documents")
async def list_documents():
    """列出所有已上传的文档。"""
    docs = vector_store.list_documents()
    return {"documents": docs}


@router.delete("/kb/documents/{doc_id}")
async def delete_document(doc_id: str):
    """删除指定文档及其所有向量。"""
    docs = vector_store.list_documents()
    if not any(d["id"] == doc_id for d in docs):
        raise HTTPException(status_code=404, detail="文档不存在")

    try:
        vector_store.delete_document(doc_id)
        return {"message": "删除成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/kb/status")
async def kb_status():
    """返回知识库状态统计。"""
    stats = vector_store.get_stats()
    return {
        "status": "ok",
        "doc_count": stats["doc_count"],
        "chunk_count": stats["chunk_count"],
    }


@router.post("/kb/search")
async def search_knowledge(req: SearchRequest):
    """手动检索知识库（调试用）。"""
    if not req.query or not req.query.strip():
        raise HTTPException(status_code=400, detail="查询内容不能为空")

    chunks = retrieve_chunks(req.query, top_k=req.top_k)
    return {
        "query": req.query,
        "results": chunks,
    }
