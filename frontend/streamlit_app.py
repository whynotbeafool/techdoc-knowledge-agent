import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.rag.chunker import chunk_pages  # noqa: E402
from app.rag.loader import load_document  # noqa: E402
from app.rag.retriever import ChromaRetriever  # noqa: E402
from app.rag.generator import generate_answer  # noqa: E402

VECTOR_STORE_DIR = PROJECT_ROOT / "data" / "vector_store"
UPLOADED_DOCS_DIR = PROJECT_ROOT / "data" / "uploaded_docs"
UPLOADED_DOCS_DIR.mkdir(parents=True, exist_ok=True)

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

    build_clicked = st.button("建立索引")

    if build_clicked:
        with st.spinner("正在解析、切分并写入向量库..."):
            retriever = ChromaRetriever(str(VECTOR_STORE_DIR))
            all_chunks = []
            for f in uploaded_files:
                dest = UPLOADED_DOCS_DIR / f.name
                dest.write_bytes(f.getbuffer())
                try:
                    pages = load_document(dest)
                    chunks = chunk_pages(pages)
                except Exception as e:
                    st.write(f"跳过 {f.name}：解析失败（{e}）")
                    continue
                all_chunks.extend(chunks)

            if all_chunks:
                retriever.index_chunks(all_chunks)
                st.success(f"已建立索引：{len(all_chunks)} 个 chunk，来自 {len(uploaded_files)} 个文件。现在可以直接提问。")
            else:
                st.write("没有可用的 chunk，索引未更新。")

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
