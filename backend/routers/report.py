"""
报告生成路由 — 接收表单参数，流式生成报告。
由前端 ReportFormModal 提交参数后调用此接口。
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse, ServerSentEvent
from typing import Optional

from services.ai_service import ai_service
from services.prompt_templates import get_report_system_prompt, build_report_prompt_from_params

router = APIRouter()


class ReportGenerateRequest(BaseModel):
    session_id: str
    report_type: str = "weekly"
    date_range: Optional[str] = None
    main_work: str = ""
    achievements: str = ""
    problems: str = ""
    next_plan: str = ""
    additional_info: Optional[str] = None


@router.post("/report/generate")
async def generate_report_stream(req: ReportGenerateRequest):
    """
    接收报告参数，流式返回 Markdown 报告。
    """
    async def event_generator():
        try:
            system_prompt = get_report_system_prompt(req.report_type)
            user_prompt = build_report_prompt_from_params(req)

            full_response = ""
            async for token in ai_service.generate_stream(
                user_message=user_prompt,
                system_prompt=system_prompt,
            ):
                full_response += token
                yield ServerSentEvent(event="token", data=token)

            yield ServerSentEvent(event="report_done", data=full_response)
            yield ServerSentEvent(event="done", data="")
        except Exception as e:
            yield ServerSentEvent(event="error", data=str(e))

    return EventSourceResponse(event_generator())
