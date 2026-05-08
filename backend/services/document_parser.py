"""
文档解析服务。
支持解析 .txt, .docx, .pdf 文件，提取纯文本。
"""
import re
from pathlib import Path
from typing import List


def parse_file(file_path: str, file_name: str) -> str:
    """
    根据文件扩展名调用对应解析器。
    返回提取的纯文本，失败时返回空字符串。
    """
    suffix = Path(file_name).suffix.lower()
    if suffix == ".txt":
        return _parse_txt(file_path)
    elif suffix in (".docx", ".doc"):
        return _parse_docx(file_path)
    elif suffix == ".pdf":
        return _parse_pdf(file_path)
    else:
        return ""


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> List[str]:
    """
    将长文本按句子边界切分为语义连贯的块。
    1. 先按段落边界（双换行）切分，保持段落完整性
    2. 段内按句子边界切分（。！？.!?；）
    3. 将句子逐条累积，满约 chunk_size 字符时成块
    4. 单句超过 chunk_size 字符 → 按中文逗号/顿号进一步拆分
    5. 相邻块之间加双向 overlap 字符重叠
    返回 List[str]。
    """
    if not text or not text.strip():
        return []
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Step 1: Split into paragraphs first (preserve paragraph integrity)
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    all_chunks = []
    for para in paragraphs:
        # Step 2: Split paragraph into sentences
        sentences = _split_into_sentences(para)

        # Step 3: Accumulate sentences into chunks
        para_chunks = _pack_sentences_into_chunks(sentences, chunk_size)
        all_chunks.extend(para_chunks)

    # Step 4: Add bidirectional overlap between consecutive chunks
    result = _add_overlap(all_chunks, overlap)

    return [c for c in result if c.strip()]


def _split_into_sentences(text: str) -> List[str]:
    """按句子边界切分：。！？.!?；以及换行"""
    # 段内换行替换为空格
    text = re.sub(r"\n", " ", text)
    # 在句子结束标点处切分
    parts = re.split(r"(?<=[。！？.!?；])\s*", text)
    return [p for p in (p.strip() for p in parts) if p]


def _pack_sentences_into_chunks(sentences: List[str], chunk_size: int) -> List[str]:
    """将句子累积成块，超过 chunk_size 时成块"""
    chunks = []
    current = []
    current_len = 0
    for sent in sentences:
        slen = len(sent)
        if slen > chunk_size:
            if current:
                chunks.append("\n".join(current))
                current = []
                current_len = 0
            sub_parts = _split_long_sentence(sent, chunk_size)
            chunks.extend(sub_parts)
        elif current_len + slen + (len(current) - 1 if current else 0) <= chunk_size:
            current.append(sent)
            current_len += slen
        else:
            if current:
                chunks.append("\n".join(current))
            current = [sent]
            current_len = slen
    if current:
        chunks.append("\n".join(current))
    return [c for c in chunks if c.strip()]


def _split_long_sentence(sent: str, chunk_size: int) -> List[str]:
    """对超长单句按中文逗号/顿号进一步拆分"""
    parts = re.split(r"(?<=[，、,])", sent)
    result = []
    current = []
    current_len = 0
    for part in parts:
        part = part.strip()
        if not part:
            continue
        plen = len(part)
        if current_len + plen <= chunk_size:
            current.append(part)
            current_len += plen
        else:
            if current:
                result.append("".join(current))
            if plen > chunk_size:
                prefix_len = len("".join(current))
                result.append(sent[prefix_len:prefix_len + chunk_size])
                remaining = sent[prefix_len + chunk_size:]
                while remaining:
                    result.append(remaining[:chunk_size])
                    remaining = remaining[chunk_size:]
                current = []
                current_len = 0
            else:
                current = [part]
                current_len = plen
    if current:
        result.append("".join(current))
    return [r for r in result if r.strip()]


def _add_overlap(chunks: List[str], overlap: int) -> List[str]:
    """
    在相邻块之间加双向重叠，确保每个 chunk 都包含上下文衔接。
    块 N 会同时包含块 N-1 的尾部和块 N+1 的首部，
    避免检索结果在关键位置截断。
    重叠量不超过相邻块长度的一半，防止小块被完全吞并。
    """
    if len(chunks) <= 1 or overlap <= 0:
        return chunks

    result = []
    for i in range(len(chunks)):
        chunk = chunks[i]
        # 向前借上下文：前一个块的尾部
        if i > 0:
            prev = chunks[i - 1]
            borrow = min(overlap, len(prev) // 2)
            if borrow > 0:
                chunk = prev[-borrow:] + chunk
        # 向后借上下文：后一个块的首部
        if i < len(chunks) - 1:
            next_chunk = chunks[i + 1]
            borrow = min(overlap, len(next_chunk) // 2)
            if borrow > 0:
                chunk = chunk + next_chunk[:borrow]
        result.append(chunk)

    return result


def _fixed_chunk(text: str, chunk_size: int, overlap: int) -> List[str]:
    """简单的固定大小切分，带重叠。"""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += chunk_size - overlap
    return [c for c in chunks if c.strip()]


def _parse_txt(file_path: str) -> str:
    """尝试多种编码读取 txt 文件。"""
    for encoding in ["utf-8", "gbk", "gb2312", "gb18030", "utf-16"]:
        try:
            with open(file_path, "r", encoding=encoding) as f:
                content = f.read()
            if content and content.strip():
                return content.strip()
        except (UnicodeDecodeError, LookupError, OSError):
            continue

    try:
        import chardet
        with open(file_path, "rb") as f:
            raw = f.read()
        detected = chardet.detect(raw)
        encoding = detected.get("encoding", "utf-8")
        result = raw.decode(encoding or "utf-8", errors="replace")
        return result.strip()
    except Exception:
        return ""


def _parse_docx(file_path: str) -> str:
    """从 .docx 文件提取所有段落文本。"""
    try:
        import docx
        doc = docx.Document(file_path)
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paragraphs)
    except Exception:
        return ""


def _parse_pdf(file_path: str) -> str:
    """从 PDF 文件提取文本。"""
    try:
        import pdfplumber
        texts = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    texts.append(page_text)
        return "\n".join(texts).strip()
    except Exception:
        return ""
