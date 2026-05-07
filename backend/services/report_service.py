"""
报告生成服务。
管理对话 session 状态，维护多轮上下文。
"""
from typing import Dict, List, Optional
from config import settings


def build_system_prompt(report_type: str, template: str) -> str:
    return f"""你是一个专业的{report_type}生成助手。请严格按照以下格式要求生成报告：

{template}

要求：
1. 严格按照上述格式生成报告，不要偏离结构
2. 报告内容基于用户提供的真实信息生成，不要编造数据
3. 语言简洁、专业，适合正式场合使用
4. 中文输出，使用 Markdown 格式
"""


def get_report_type_label(report_type: str) -> str:
    labels = {
        "daily": "日报",
        "weekly": "周报",
        "monthly": "月报",
        "custom": "自定义报告",
    }
    return labels.get(report_type, "报告")


class SessionStore:
    def __init__(self):
        self._sessions: Dict[str, Dict] = {}

    def create_session(self, session_id: str, report_type: str, template: str):
        self._sessions[session_id] = {
            "report_type": report_type,
            "template": template,
            "history": [],
            "system_prompt": build_system_prompt(
                get_report_type_label(report_type), template
            ),
        }

    def get_session(self, session_id: str) -> Optional[Dict]:
        return self._sessions.get(session_id)

    def add_message(
        self, session_id: str, role: str, content: str
    ):
        session = self._sessions.get(session_id)
        if session:
            session["history"].append({"role": role, "content": content})

    def clear_session(self, session_id: str):
        if session_id in self._sessions:
            del self._sessions[session_id]


session_store = SessionStore()
