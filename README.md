# TechDocKnowledgeAgent

> 面向技术文档的 RAG 智能知识库问答系统,支持 PDF/Markdown/txt 上传、语义检索、引用溯源和 Docker 一键部署。

## 项目背景

技术文档数量庞大,传统关键词搜索效率低。本项目基于 RAG,让用户通过自然语言提问,从文档中获得带引用来源的答案。

## 技术栈

- Backend: FastAPI
- Frontend: Streamlit
- RAG Pipeline: Custom pipeline in Phase 1; LangChain/LangGraph in later phases
- Vector DB: Chroma / Qdrant
- Embedding: bge-m3 / text-embedding-3-small / Qwen embedding
- LLM: DeepSeek API / Qwen API
- Retrieval: BM25 + vector search + rerank in Phase 2
- Deployment: Docker + docker-compose

## 架构图

_(TODO: 补充 architecture.png,放入 docs/)_

## 功能截图

_(TODO: Phase 1 完成后补充至少 3 张截图,放入 docs/demo_screenshots/)_

## 本地运行

```bash
# 1. install dependencies
pip install -r backend/requirements.txt
cp .env.example .env

# 2. start backend
uvicorn backend.app.main:app --reload

# 3. start frontend
streamlit run frontend/streamlit_app.py
```

## Docker 一键启动

```bash
docker compose up --build
# frontend: http://localhost:8501
# backend docs: http://localhost:8000/docs
```

## 项目状态

- [ ] Phase 1 MVP:上传 -> 解析 -> 切分 -> 向量检索 -> 问答 -> 引用溯源
- [ ] Phase 2:混合检索(BM25 + 向量)、Rerank、评测集、轻量 Agent 节点

## 后续规划

详见项目求职计划文档中的 Phase 2 迭代功能(混合检索、Rerank、多轮追问、评测集、日志与成本记录)。
