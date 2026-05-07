# 后端服务

## 环境配置

复制 `.env.example` 为 `.env` 并填入配置：

```env
# DeepSeek 测试
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_API_KEY=your-api-key
OPENAI_MODEL=deepseek-chat

# 内网部署
# OPENAI_BASE_URL=http://your-internal-model-host/v1
# OPENAI_API_KEY=your-internal-key
# OPENAI_MODEL=kimi2.5

# Embedding 模型服务（OpenAI 兼容接口，由外部独立部署）
EMBEDDING_BASE_URL=http://localhost:8001/v1
EMBEDDING_API_KEY=your-embedding-api-key
EMBEDDING_MODEL=text-embedding-3-small
```

> 注意：Embedding 模型不本地下载，需要额外启动一个 OpenAI 兼容的 embedding 模型服务（如 text-embedding-3-small、bge 等），并在 `.env` 中配置对应的 `EMBEDDING_BASE_URL`、`EMBEDDING_API_KEY`、`EMBEDDING_MODEL`。

## 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

## 启动服务

```bash
python main.py
# 或
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## API 接口

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/health` | 健康检查 |
| POST | `/api/chat/session` | 创建新对话会话 |
| POST | `/api/chat/stream` | 流式对话（SSE）|
| POST | `/api/chat/clear` | 清除会话 |
| GET | `/api/chat/history/{session_id}` | 获取对话历史 |
| POST | `/api/generate` | 表单模式生成报告 |
| POST | `/api/export/word` | 导出 Word |
| POST | `/api/export/pdf` | 导出 PDF |

## Word 模板

将用户提供的 Word 模板文件放置于 `templates/word_template.docx`，程序将自动使用该模板格式导出。

## PDF 字体

将中文字体文件（如 SourceHanSansCN.ttf）放置于 `fonts/` 目录，用于 PDF 导出。
