import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.rag.retriever import ChromaRetriever  # noqa: E402
from app.rag.generator import generate_answer  # noqa: E402

VECTOR_STORE_DIR = PROJECT_ROOT / "data" / "vector_store"

st.set_page_config(page_title="TechDocKnowledgeAgent", layout="wide")

st.title("TechDocKnowledgeAgent")
st.caption("面向技术文档的 RAG 智能知识库问答系统")

# --- 上传区 ---
st.markdown("### 上传文档")
uploaded_files = st.file_uploader(
    "上传技术文档（PDF/Markdown/txt）",
    type=["pdf", "md", "txt"],
    accept_multiple_files=True,
)
if uploaded_files:
    st.write(f"已选择 {len(uploaded_files)} 个文件：")
    for f in uploaded_files:
        st.write(f"- {f.name}")
    st.caption("当前版本仅展示已选文件；请先用 scripts/build_index.py 建索引，网页上传入库将在后续版本加入。")

# --- 提问框 ---
st.markdown("### 提问")
question = st.text_input("请输入你的问题：")
ask_clicked = st.button("提问")

# --- 回答区 + 引用区 ---
if ask_clicked and question:
    with st.spinner("正在检索并生成回答..."):
        retriever = ChromaRetriever(str(VECTOR_STORE_DIR))
        chunks = retriever.query_chunks(question, top_k=5)

        if not chunks:
            st.write("检索不到任何相关资料，请先运行 scripts/build_index.py 建立索引。")
        else:
            answer = generate_answer(question, chunks)

            st.markdown("### 回答")
            st.write(answer)

            st.markdown("### 引用来源")
            for c in chunks:
                st.write(f"- {c['source']} 第{c['page']}页 (chunk_id={c['chunk_id']})")
