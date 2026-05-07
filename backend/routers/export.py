"""
导出路由 — Word 和 PDF 导出。
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from services.export_service import export_to_word, export_to_pdf
from paths import WORD_TEMPLATE_PATH

router = APIRouter()


class ExportRequest(BaseModel):
    content: str
    filename: str = "report"


@router.post("/export/word")
async def export_word(req: ExportRequest):
    try:
        template_path = None
        if WORD_TEMPLATE_PATH.exists():
            template_path = str(WORD_TEMPLATE_PATH)

        data = export_to_word(req.content, template_path=template_path)
        return Response(
            content=data,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f'attachment; filename="{req.filename}.docx"'
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export/pdf")
async def export_pdf(req: ExportRequest):
    try:
        data = export_to_pdf(req.content)
        return Response(
            content=data,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{req.filename}.pdf"'
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
