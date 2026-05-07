"""
报告生成路由 — 表单模式一次性生成。
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from services.ai_service import ai_service
from services.prompt_templates import get_default_template, build_form_prompt

router = APIRouter()


class GenerateRequest(BaseModel):
    report_type: str = "daily"
    date_range: Optional[str] = None
    main_work: str = ""
    achievements: str = ""
    problems: str = ""
    next_plan: str = ""
    additional_info: Optional[str] = None


class GenerateResponse(BaseModel):
    content: str


@router.post("/generate", response_model=GenerateResponse)
async def generate_report(req: GenerateRequest):
    try:
        prompt = build_form_prompt(req)
        system_prompt = get_default_template(req.report_type)

        content = await ai_service.generate(
            user_message=prompt,
            system_prompt=system_prompt,
        )
        return GenerateResponse(content=content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
