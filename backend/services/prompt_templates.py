"""
Prompt 模板服务。
提供 RAG、闲聊、报告生成等系统提示词。
"""


REPORT_FORMATS = {
    "daily": ("日报", "一、今日工作完成情况", "三、明日工作计划", "2026年4月30日"),
    "weekly": ("周报", "一、本周工作完成情况", "三、下周工作计划", "2026年4月20日-4月26日"),
    "monthly": ("月报", "一、本月工作完成情况", "三、下月工作计划", "2026年4月"),
    "quarterly": ("季度工作报告", "一、本季度工作完成情况", "三、下季度工作计划", "2026年Q2"),
    "custom": ("工作报告", "一、工作完成情况", "三、下一步工作计划", ""),
}


def _report_config(report_type: str):
    return REPORT_FORMATS.get(report_type, REPORT_FORMATS["weekly"])


def get_default_template(report_type: str) -> str:
    """表单生成报告时使用的系统提示。"""
    type_name, module1, module3, default_date = _report_config(report_type)
    return f"""你是一个专业的工作报告生成助手。请输出干净的中文报告正文。

固定版式：
{type_name}
{default_date}

{module1}
1、第一项工作内容。
2、第二项工作内容。
3、第三项工作内容。

二、存在的问题
1、存在的问题或风险。
2、如无明显问题，写“暂无明显问题，后续将持续关注执行过程中的细节风险。”。

{module3}
1、下一步计划。
2、改进或跟进措施。
3、复盘、验证或协作计划。

格式要求：
- 不要输出 Markdown 标题符号或代码块。
- 编号必须使用中文顿号格式，例如“1、”。
- 禁止使用英文点号编号。
- 每条内容 40-90 字，以中文句号结尾。
- 只输出报告正文，不要解释说明。"""


def get_rag_system_prompt(rag_context: str = "") -> str:
    """知识库问答的 system prompt。"""
    base = """你是一个专业、准确的知识库问答助手。

要求：
1. 优先根据知识库参考内容回答。
2. 如果参考内容与问题无关或不足以回答，请忽略参考内容，直接基于你的知识回答。
3. 回答要简洁、清晰、有条理。
4. 不确定时要诚实说明。"""
    if rag_context:
        return f"{base}\n\n【知识库参考内容】\n{rag_context}\n\n请结合上述参考内容回答用户问题。"
    return base


def get_chat_system_prompt() -> str:
    """闲聊 system prompt。kb_mode=false 时使用，不检索知识库。"""
    return """你是一个友好、智能的中文助手。

要求：
1. 回答自然、亲切、有礼貌。
2. 内容简洁，不要冗长。
3. 可以讨论工作、技术、生活等话题。
4. 遇到不确定的问题时诚实说明。"""


def get_report_system_prompt(report_type: str, extracted_data: dict = None, user_message: str = "") -> str:
    """报告生成的 system prompt，根据用户输入扩写生成中文报告。"""
    type_name, module1, module3, default_date = _report_config(report_type)

    date_range = default_date
    if extracted_data:
        dr = (extracted_data.get("date_range") or "").strip()
        if dr:
            date_range = dr

    raw_work = ""
    if extracted_data:
        raw_work = extracted_data.get("main_work") or ""
    if not raw_work and user_message:
        raw_work = user_message

    return f"""你是一位专业的工作报告撰写专家。请根据用户提供的工作内容，生成一份正式、清晰、适合直接提交的{type_name}。

【报告日期】
{date_range}

【用户工作描述】
{raw_work or "用户未提供具体工作内容，请基于常识生成通用报告。"}

【输出格式】
不要输出 Markdown 标题符号，不要输出代码块。
编号必须使用中文顿号格式，不要使用英文点号编号。

请严格按以下版式输出：

{type_name}
{date_range}

{module1}
1、在用户原始工作内容基础上扩写第一项工作，补充具体动作、成果、影响或推进情况，保持一行完整表达。
2、在用户原始工作内容基础上扩写第二项工作，补充具体问题、处理过程、结果或协作情况，保持一行完整表达。
3、在用户原始工作内容基础上扩写第三项工作；如果用户未提供第三项，可结合已有内容合理推断后续相关工作。

二、存在的问题
1、结合用户工作内容分析实际存在的问题、风险、阻塞点或需要持续优化的事项。
2、如果用户没有提到明显问题，可写“暂无明显问题，后续将继续关注执行过程中的细节风险。”。

{module3}
1、结合已完成工作安排下一步具体计划，说明要推进的事项、目标或交付结果。
2、结合存在的问题安排改进措施或跟进计划，避免空泛表达。
3、补充一项合理的协作、复盘、优化或验证计划。

【格式铁律】
- 只输出报告正文，不要解释、客套话、引导语。
- 绝对不要出现 Markdown 标题符号、Markdown 代码块。
- 所有编号必须是“1、”这种中文顿号编号，禁止英文点号编号。
- 每个模块标题独占一行，模块标题后直接换行进入编号列表。
- 每条编号内容控制在 40-90 字，以中文句号“。”结尾。
- 不要在编号和正文之间插入多余换行。"""


def extract_work_prompt(user_message: str) -> str:
    """构建提炼 prompt，让 LLM 从用户输入中提取工作内容，输出 JSON。"""
    return f"""你是一个专业的报告内容提炼助手。请只从用户输入中提取工作信息，忠实保留用户表达，不扩写、不编造。

【用户输入】
{user_message}

【输出要求】
只返回标准 JSON，不要输出 Markdown，不要输出解释文字。字段如下：
{{
  "main_work": "提炼后的工作内容，保留用户关键事项，可用换行分隔多项工作",
  "problems": "用户明确提到的问题；没有则返回空字符串",
  "next_plan": "用户明确提到的下一步计划；没有则返回空字符串",
  "date_range": "时间范围，例如 今日、本周、本月、2026年4月；没有则返回空字符串",
  "type": "daily/weekly/monthly/quarterly/custom"
}}

注意：
- 只能返回 JSON 对象。
- 不要添加用户没有提供的事实。
- 不要把报告正文写在这里。"""


def build_form_prompt(req) -> str:
    """构建表单模式报告 prompt。"""
    return f"""报告类型：{getattr(req, "report_type", "weekly")}
时间范围：{getattr(req, "date_range", "") or ""}
主要工作：{getattr(req, "main_work", "") or ""}
工作成果：{getattr(req, "achievements", "") or ""}
存在问题：{getattr(req, "problems", "") or ""}
后续计划：{getattr(req, "next_plan", "") or ""}
补充信息：{getattr(req, "additional_info", "") or ""}"""


def build_report_prompt_from_params(req) -> str:
    """构建流式表单报告 prompt。"""
    return build_form_prompt(req)
