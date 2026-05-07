"""
对话路由 — 三意图路由入口。
支持：1. 工作报告（周报/日报/月报/季度报告） 2. 知识库问答 3. 闲聊

流程：用户消息 → 意图判断（关键词匹配）
  → 工作报告：LLM 从自然语言提取工作内容并扩写生成
  → 知识库问答：RAG 检索 → LLM 回答（知识库无相关内容时走闲聊）
  → 闲聊：直接 LLM 回答
"""
import json
import traceback
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse, ServerSentEvent

from services.ai_service import ai_service
from services.rag_service import retrieve_context, retrieve_chunks, DEFAULT_TOP_K
from services.prompt_templates import (
    get_rag_system_prompt,
    get_report_system_prompt,
    build_report_prompt_from_chat,
    extract_work_prompt,
    get_chat_system_prompt,
)

router = APIRouter()


class ChatRequest(BaseModel):
    session_id: str
    message: str
    kb_mode: bool = False  # 前端点亮知识库按钮时为 True，此时强制走 RAG 路由


class NewSessionRequest(BaseModel):
    pass


# ---------------------------------------------------------------------------
# 意图判断 — 关键词匹配
# ---------------------------------------------------------------------------

REPORT_PATTERNS = [
    r"周报", r"日报", r"月报", r"季度报告",
    r"工作汇报", r"工作总结",
    r"写周报", r"写日报", r"写月报", r"生成周报", r"生成日报", r"生成月报",
    r"本周工作", r"今日工作", r"本月工作",
    r"季度总结", r"季度汇报",
]


def _is_report_intent(message: str) -> bool:
    """判断是否触发工作报告生成意图。"""
    import re
    msg = message.strip()
    for pattern in REPORT_PATTERNS:
        if re.search(pattern, msg):
            return True
    # 检测是否像工作内容列表（多行，含序号或项目符号）
    lines = [l.strip() for l in msg.split("\n") if l.strip()]
    if len(lines) >= 2:
        # 匹配有序列表（1. 2. 3.）或无序列表（- *）
        list_pattern = re.compile(r"^[\d一二三四五六七八九十]+[.、)）]\s|^[-*●]\s")
        if sum(1 for l in lines if list_pattern.match(l)) >= 2:
            return True
        # 匹配常见工作动作词（单行消息不走这里，避免误判）
        work_verbs = ["完成了", "优化了", "修复了", "开发了", "推进了", "上线了", "调试了", "部署了", "测试了", "解决了", "调研了", "设计了", "整理了", "编写了", "提交了", "联调了"]
        if sum(1 for l in lines for v in work_verbs if v in l) >= 1:
            return True
    return False


def _detect_report_type(message: str) -> str:
    """从消息中判断报告类型。"""
    msg = message
    if "日报" in msg or "今日" in msg or "本日" in msg or "本周" not in msg and "本月" not in msg:
        # 如果没有明确的周/月报标识，且消息看起来像日工作内容
        if not any(k in msg for k in ["周报", "本周", "下周", "月报", "本月", "下月", "季度"]):
            # 通过日期判断
            import re
            date_pattern = re.compile(r"(\d{1,2})[号日]|\d{4}[-/]\d{1,2}[-/]")
            if date_pattern.search(msg):
                return "daily"
    if "月报" in msg or "本月" in msg or "月度" in msg:
        return "monthly"
    if "季度" in msg or "季度报告" in msg:
        return "quarterly"
    return "weekly"


# ---------------------------------------------------------------------------
# Session store
# ---------------------------------------------------------------------------

_sessions: dict = {}


def _get_or_create_session(session_id: str) -> dict:
    if session_id not in _sessions:
        _sessions[session_id] = {"history": []}
    return _sessions[session_id]


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------

@router.post("/chat/session")
async def create_session(req: NewSessionRequest):
    session_id = str(uuid.uuid4())
    _sessions[session_id] = {"history": []}
    return {"session_id": session_id}


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    session = _get_or_create_session(req.session_id)
    history = session["history"]
    user_message = req.message.strip()
    history.append({"role": "user", "content": user_message})

    # 知识库模式：强制走 RAG 路由，跳过意图判断
    if req.kb_mode:
        return await _handle_general_intent(req, session, use_kb=True)

    # 正常模式：按意图判断
    if _is_report_intent(user_message):
        return await _handle_report_intent(req, session)
    else:
        return await _handle_general_intent(req, session, use_kb=False)


# ---------------------------------------------------------------------------
# 工作报告路由
# ---------------------------------------------------------------------------

async def _handle_report_intent(req: ChatRequest, session: dict):
    history = session["history"]
    report_type = _detect_report_type(req.message)

    async def event_generator():
        try:
            yield ServerSentEvent(
                event="intent",
                data=json.dumps({
                    "intent": "report_generate",
                    "report_type": report_type,
                }, ensure_ascii=False),
            )

            # ---- 阶段一：提炼工作内容（一次性调用，非流式） ----
            yield ServerSentEvent(
                event="stage",
                data=json.dumps({"stage": "extracting"}, ensure_ascii=False),
            )
            extract_prompt = extract_work_prompt(req.message)
            extracted = await ai_service.generate(
                user_message=extract_prompt,
                history=history[:-1],
            )
            try:
                extracted_data = json.loads(extracted)
            except json.JSONDecodeError:
                extracted_data = {"main_work": req.message, "problems": "", "next_plan": "", "date_range": "", "type": report_type}

            yield ServerSentEvent(
                event="stage",
                data=json.dumps({"stage": "generating", **extracted_data}, ensure_ascii=False),
            )

            # ---- 阶段二：生成结构化报告（流式） ----
            system_prompt = get_report_system_prompt(report_type, extracted_data, req.message)
            user_message = f"请根据以上信息，生成一份专业的{type_name}。"

            full_response = ""
            async for token in ai_service.generate_stream(
                user_message=user_message,
                system_prompt=system_prompt,
                history=[],
            ):
                full_response += token
                yield ServerSentEvent(event="token", data=token)

            history.append({"role": "assistant", "content": full_response})
            yield ServerSentEvent(event="done", data="")

        except Exception as e:
            error_msg = str(e) if str(e) else repr(e)
            traceback.print_exc()
            yield ServerSentEvent(event="error", data=f"{error_msg}\n{traceback.format_exc()}")

    return EventSourceResponse(event_generator())


# ---------------------------------------------------------------------------
# 知识库问答 / 闲聊路由
# ---------------------------------------------------------------------------

async def _handle_general_intent(req: ChatRequest, session: dict, use_kb: bool = True):
    history = session["history"]

    async def event_generator():
        try:
            if use_kb:
                rag_chunks = retrieve_chunks(req.message, top_k=DEFAULT_TOP_K)
                rag_context = retrieve_context(req.message)
                yield ServerSentEvent(
                    event="kb_context",
                    data=json.dumps({"chunks": rag_chunks, "context": rag_context}, ensure_ascii=False),
                )
                system_prompt = get_rag_system_prompt(rag_context)
            else:
                system_prompt = get_chat_system_prompt()

            full_response = ""

            async for token in ai_service.generate_stream(
                user_message=req.message,
                system_prompt=system_prompt,
                history=history[:-1],
            ):
                full_response += token
                yield ServerSentEvent(event="token", data=token)

            history.append({"role": "assistant", "content": full_response})
            yield ServerSentEvent(event="done", data="")

        except Exception as e:
            error_msg = str(e) if str(e) else repr(e)
            traceback.print_exc()
            yield ServerSentEvent(event="error", data=f"{error_msg}\n{traceback.format_exc()}")

    return EventSourceResponse(event_generator())


# ---------------------------------------------------------------------------
# 其他端点
# ---------------------------------------------------------------------------

@router.post("/chat/clear")
async def clear_session(session_id: str):
    if session_id in _sessions:
        del _sessions[session_id]
    return {"status": "ok"}


@router.get("/chat/history/{session_id}")
async def get_history(session_id: str):
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在或已过期")
    return {"history": session["history"]}
