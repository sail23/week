from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from config import settings
from routers import generate, export, chat, report, knowledge_base
from paths import ensure_directories

ensure_directories()

app = FastAPI(
    title="Week Report API",
    description="周报日报生成器后端服务",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api", tags=["对话"])
app.include_router(generate.router, prefix="/api", tags=["报告生成"])
app.include_router(report.router, prefix="/api", tags=["报告生成"])
app.include_router(export.router, prefix="/api", tags=["导出"])
app.include_router(knowledge_base.router, prefix="/api", tags=["知识库"])


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "model": settings.openai_model,
        "base_url": settings.openai_base_url,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
