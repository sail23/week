"""
对话路由：报告生成、知识库问答、闲聊。
"""
import json
import re
import traceback
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse, ServerSentEvent

from services.ai_service import ai_service
from services.rag_service import DEFAULT_TOP_K, retrieve_chunks, retrieve_context
from services.prompt_templates import (
    extract_work_prompt,
    get_chat_system_prompt,
    get_rag_system_prompt,
    get_report_system_prompt,
)

router = APIRouter()


class ChatRequest(BaseModel):
    session_id: str
    message: str
    kb_mode: bool = False


class NewSessionRequest(BaseModel):
    pass


REPORT_PATTERNS = [
    r"周报", r"日报", r"月报", r"季度报告",
    r"工作汇报", r"工作总结",
    r"写周报", r"写日报", r"写月报",
    r"生成周报", r"生成日报", r"生成月报",
    r"本周工作", r"今日工作", r"本月工作",
    r"季度总结", r"季度汇报",
]

REPORT_TYPE_NAMES = {
    "daily": "日报",
    "weekly": "周报",
    "monthly": "月报",
    "quarterly": "季度报告",
    "custom": "工作报告",
}

_sessions: dict = {}


def _get_or_create_session(session_id: str) -> dict:
    if session_id not in _sessions:
        _sessions[session_id] = {"history": []}
    return _sessions[session_id]


def _is_report_intent(message: str) -> bool:
    """判断是否触发工作报告生成意图。"""
    msg = message.strip()
    for pattern in REPORT_PATTERNS:
        if re.search(pattern, msg):
            return True

    lines = [line.strip() for line in msg.split("\n") if line.strip()]
    if len(lines) >= 2:
        list_pattern = re.compile(r"^[\d一二三四五六七八九十]+[.、)）]\s*|^[-*●]\s*")
        if sum(1 for line in lines if list_pattern.match(line)) >= 2:
            return True

        work_verbs = [
            "完成了", "优化了", "修复了", "开发了", "推进了", "上线了",
            "调试了", "部署了", "测试了", "解决了", "调研了", "设计了",
            "整理了", "编写了", "提交了", "联调了",
        ]
        if any(verb in line for line in lines for verb in work_verbs):
            return True
    return False


def _detect_report_type(message: str) -> str:
    """从消息中判断报告类型。"""
    if "月报" in message or "本月" in message or "月度" in message:
        return "monthly"
    if "季度" in message or "季度报告" in message:
        return "quarterly"
    if "日报" in message or "今日" in message or "本日" in message:
        return "daily"
    return "weekly"


def _normalize_report_output(content: str) -> str:
    """将模型输出归一化为干净的中文报告格式。"""
    if not content:
        return ""

    text = content.strip()
    text = re.sub(r"```(?:markdown|md)?\s*", "", text, flags=re.IGNORECASE)
    text = text.replace("```", "")

    lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            lines.append("")
            continue

        line = line.replace("**", "")
        line = re.sub(r"^#{1,6}\s*", "", line)
        line = re.sub(r"^(\d+)\.\s*", r"\1、", line)
        line = re.sub(r"^(\d+)\)\s*", r"\1、", line)
        line = re.sub(r"^（(\d+)）\s*", r"\1、", line)
        line = re.sub(r"^(\d+、)\s+", r"\1", line)
        lines.append(line)

    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"(?m)^(\d+、)\s*\n+", r"\1", text)
    return text.strip()


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

    if not user_message:
        raise HTTPException(status_code=400, detail="消息不能为空")
    if len(user_message) > 20000:
        raise HTTPException(status_code=400, detail="消息过长，请精简后重试")

    history.append({"role": "user", "content": user_message})

    if req.kb_mode:
        return await _handle_general_intent(req, session, use_kb=True)
    if _is_report_intent(user_message):
        return await _handle_report_intent(req, session)
    return await _handle_general_intent(req, session, use_kb=False)


async def _handle_report_intent(req: ChatRequest, session: dict):
    history = session["history"]
    report_type = _detect_report_type(req.message)

    async def event_generator():
        try:
            yield ServerSentEvent(
                event="intent",
                data=json.dumps({"intent": "report_generate", "report_type": report_type}, ensure_ascii=False),
            )

            yield ServerSentEvent(
                event="stage",
                data=json.dumps({"stage": "extracting"}, ensure_ascii=False),
            )

            extracted = await ai_service.generate(
                user_message=extract_work_prompt(req.message),
                system_prompt="你是一个专业的工作内容提炼助手。只从用户输入中提取工作信息，严格返回 JSON。不添加、不扩写、不编造。",
                history=[],
            )
            try:
                raw = extracted.strip()
                if raw.startswith("```"):
                    raw = raw.split("\n", 1)[-1]
                    if raw.endswith("```"):
                        raw = raw[:-3]
                extracted_data = json.loads(raw)
            except json.JSONDecodeError:
                clean_message = re.sub(r"【[^】]+】", "", req.message).strip()
                extracted_data = {
                    "main_work": clean_message,
                    "problems": "",
                    "next_plan": "",
                    "date_range": "",
                    "type": report_type,
                }

            yield ServerSentEvent(
                event="stage",
                data=json.dumps({"stage": "generating", **extracted_data}, ensure_ascii=False),
            )

            type_name = REPORT_TYPE_NAMES.get(report_type, "工作报告")
            generated = await ai_service.generate(
                user_message=f"请根据以上信息，生成一份专业的{type_name}。",
                system_prompt=get_report_system_prompt(report_type, extracted_data, req.message),
                history=[],
            )
            full_response = _normalize_report_output(generated)
            yield ServerSentEvent(event="token", data=full_response)

            history.append({"role": "assistant", "content": full_response})
            yield ServerSentEvent(event="done", data="")
        except Exception as e:
            error_msg = str(e) if str(e) else repr(e)
            traceback.print_exc()
            yield ServerSentEvent(event="error", data=error_msg)

    return EventSourceResponse(event_generator())


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
                system_prompt = get_rag_system_prompt(rag_context) if rag_context.strip() else get_chat_system_prompt()
            else:
                system_prompt = get_chat_system_prompt()

            full_response = ""
            pending = ""
            async for token in ai_service.generate_stream(
                user_message=req.message,
                system_prompt=system_prompt,
                history=history[:-1],
            ):
                full_response += token
                if not token.strip():
                    pending += token
                else:
                    yield ServerSentEvent(event="token", data=pending + token)
                    pending = ""
            if pending:
                yield ServerSentEvent(event="token", data=pending)

            history.append({"role": "assistant", "content": full_response})
            yield ServerSentEvent(event="done", data="")
        except Exception as e:
            error_msg = str(e) if str(e) else repr(e)
            traceback.print_exc()
            yield ServerSentEvent(event="error", data=error_msg)

    return EventSourceResponse(event_generator())


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
