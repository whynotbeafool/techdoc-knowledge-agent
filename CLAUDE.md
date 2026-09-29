# TechDocKnowledgeAgent — 项目上下文

给任何一台机器上的 Claude Code 看的交接说明。**开始改动之前先读完这份文件。**

## 这个项目是什么

面向技术文档的 RAG 知识库问答系统，**同时服务两个目的，优先级不同**：

1. **主线（研究）**：2027 年国内博士申请的研究型代表作。目标是一份可复现的评测基准 +
   8-12 页研究稿，方向是技术文档场景下的证据锚定检索与可验证生成。
2. **副线（求职）**：2026 下半年 AI 应用开发岗位的作品集项目。

**主次已定：按研究标准做，求职材料作为副产品掉出来，不是反过来。**
原因是研究级标注（证据段落级）无法由求职级标注（只标答案）升级得到，先做低标准会导致全部重标。

两条研究问题：

- **RQ1**：BM25 / Dense / Hybrid / Rerank / Long-context / no-RAG 在技术文档问答中的检索效果差异。
- **RQ3**：引用校验、证据覆盖与拒答机制能在多大程度上降低幻觉、提高可验证性。

## 协作方式（重要，不要跳过）

用户正在**主动训练自己的工程能力**，不是要一个代写服务。约定如下：

1. **写在前、审在后**：新功能由**用户先写一版**（哪怕写错、写不完），Claude 做 review 和纠正，
   不要默认直接产出成品代码。用户能独立完成单概念的代码；多步骤组合逻辑仍需带解释的示范。
2. **调试纪律**：报错时先让用户读 traceback、提出假设，再给答案。
3. **精力分配**：核心 RAG 逻辑（chunking / retrieval / prompt / citation）优先由用户手写；
   外围脚手架（Docker、样板路由、UI 布局）可以 AI 辅助，理解思路即可。
4. **不要在用户表达悲观判断时附加安慰话**。用户明确区分"客观判断"与"情绪状态"，
   只回应实质内容。

## 绝对不能破坏的不变量

这些每一条都是踩过坑或经过论证才定下来的，改动前必须理解代价。

| 不变量 | 为什么 |
|---|---|
| 证据锚定用 canonical text 的字符偏移，**绝不用 `chunk_id`** | chunk_id 的序号依赖切分参数，做 chunk 消融时会全部错位，标注即作废 |
| 偏移是**零基半开区间、Unicode 码点**（Python `str` 下标），不是 UTF-8 字节 | 语料含多字节字符，按字节解释会让首个非 ASCII 字符之后的偏移全错 |
| `chunk.text == canonical_text[start:end]` 恒成立，有测试断言 | 这条不变量把一整类坐标错位 bug 从"靠人肉小心"变成"CI 会拦住" |
| `.gitattributes` 把 `data/corpus/canonical/**` 标为 `-text` | Windows 的 `core.autocrlf` 会在 checkout 时改写字节，破坏 `text_hash` 和所有偏移。**CI 跑在 Linux 上，测不出这个**，靠 `tests/test_corpus_integrity.py` 兜底 |
| 金标准 `data/eval/qa.jsonl` 与实验结果 `results/runs/` 严格分离 | 真值一次标定、版本固定；混写会让真值被系统输出污染 |
| **不得用实验结果反向修改标注** | 某条基线漏召回不能成为改金标准的理由。见 `data/eval/hesitations.md` 最后一条 |
| canonical 产物不可变；内容变了必须升 `revision` | `revision` 标识一份不可变产物，源文件变或提取流程变（pypdf 版本、分隔符、规范化）都要升 |
| manifest 保留历史，实验只索引 `active-revisions.json` 选中的版本 | 同一文档的多个 revision 同时进索引会混合过期语料；切换 active 后，旧 gold revision 也不得静默进入新运行 |
| 30 题阶段全部 `split: dev`，不切 test | 20 题的 test 集置信区间无法支撑结论；100 题后才切 held-out |

## 当前状态

- **Phase 1 MVP 完成**：上传 → 解析 → 切分 → 向量检索 → 问答 → 引用溯源，错误处理、Docker、
  架构图、截图齐备。
- **评测基础设施完成**：冻结语料（5 份文档，哈希校验）→ active revision 选择 → 标注校验 →
  BM25/Dense → Evidence Recall@K / 完整证据命中率 / MRR → 双 cohort 与双分层轴汇总。
- **30 题 dev 集已冻结**：29 条 confirmed、1 条 needs_review；五类各 6 题，新增有证据题的
  low / medium / high 为 7 / 7 / 6，五份 active 语料各覆盖 4 道新增有证据题。冻结哈希和
  14 题正式复标子集见 `data/eval/reannotation-plan.md`。当前冻结检索运行是 `frozen-30-hybrid-rrf-v1`；另有 BM25 生成运行。
- **q016/q017 时间隔离裁决完成**：首标后间隔 19 天，均按现行必要中间实体规则保持
  `multi_hop` 并转为 confirmed；这是提前质控，不替代 30 题冻结后预先抽取的 14 题正式复标。
- **语料审计修复完成**：错误的 PEP 8 404 页面保留为历史 `v1`，有效正文加入为 `v2` 并设为 active。
- **14 题独立上下文 AI 复标已锁定归档**：见 `research/REANNOTATION_REPORT.md`。
  不等同于已验证的人类延迟自我标注信度。核查报告确认的问题已在 `0188399` 修复并推送。
- **2026-09-28 研究推进**：覆盖规范与 FinBen/RAGAS/Self-RAG 当前论断核查已完成；
  新文字覆盖诊断和稿件更新见 `research/PROGRESS_20260928.md`。A/B/C 开发协议与离线原型亦已完成，
  见 `research/PROTOCOL_IMPLEMENTATION_20260928.md`；全套 206 passed，尚无新生成或语义标签。

## 下一步任务清单

1. 按 `research/PROTOCOL.md` 补齐候选阈值回放与日志集成；生成配置、语义标注安排、调用预算和独立测试集仍待落实。当前只有开发协议及离线原型，不能声称正式门控实验完成。
2. 原 30 题保留为 dev；新增数据需新版本协议，不因 baseline 表现回改旧 gold。q010/q021 的范围问题按 `research/PROGRESS_20260928.md` 保留并在新题版本中处理。
3. 指定三篇论文当前论断已核查，不等于完整新颖性审查；针对下一阶段问题扩展文献，之后才扩数据、调参和运行消融。投稿版式最后处理。

## 跨机器工作

### 一次性准备

```bash
git clone https://github.com/whynotbeafool/techdoc-knowledge-agent.git
cd techdoc-knowledge-agent
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
```

### clone 之后立刻可做（已验证）

冻结语料和标注集都在版本库里，所以**不需要原始 PDF、也不需要 API key**：

```bash
python scripts/validate_eval.py                          # 标注校验
python scripts/evaluate_retrieval.py --run-id <新名字>   # BM25 + Dense 评测
python -m pytest tests/ -q && ruff check .
```

标注、评测、改规范、写论文——研究主线的全部工作都能在任意机器上做。

### 需要额外准备的（只影响 MVP 演示，不影响研究主线）

| 缺什么 | 影响 | 怎么办 |
|---|---|---|
| `.env`（`DEEPSEEK_API_KEY`） | `scripts/ask.py`、Streamlit 问答 | `cp .env.example .env` 后手工填 key。**不要提交** |
| `data/raw_docs/*.pdf` 等 5 份源文档 | `build_canonical.py`、`build_index.py` | 从公开地址重新下载；或从另一台机器手工拷贝。语料已冻结，日常研究用不到它们 |
| `data/vector_store/` | Streamlit 演示 | `python scripts/build_index.py` 重建（需要 raw_docs） |

### 两台机器可以并行，但要按文件类型分工

**不需要固定在一台机器上工作。** 冲突风险取决于改的是哪类文件，不取决于机器。

| 可以并行改 | 为什么安全 |
|---|---|
| `data/eval/qa.jsonl` | 已冻结，不再按旧槽位流程追加或回改；新数据使用新版本文件与协议 |
| `results/runs/*` | 每次 run 独立文件，且 `evaluate_retrieval.py` 拒绝覆盖已存在的 run_id |
| `data/corpus/**` | 冻结后不可变，不会被编辑 |
| 代码与测试 | git 常规合并 |

| 不要并行改 | 为什么 |
|---|---|
| `docs/annotation-guideline.md`、`data/eval/hesitations.md`、`data/eval/annotation-plan.md`、`CLAUDE.md` | 散文，整体重写，合并代价高且容易改错语义 |

**`data/eval/annotation-plan.json` 是槽位的权威来源**，同时承担进度追踪和多机分工两个职责。

以下是冻结前的历史标注流程；当前 QA 已冻结，不再用于认领或追加新题：

```bash
git pull
python scripts/check_annotation_plan.py   # 看 Next pending，认领槽位后再动手
# ...标注...
python scripts/validate_eval.py && python scripts/check_annotation_plan.py
git push
```

### 平台差异

- 本项目在 **Windows（PowerShell）** 和 **macOS/Linux（bash）** 上都能跑，
  但两边的 shell 语法不同，跨机器抄命令时注意。
- macOS 默认不做 CRLF 转换，但 `.gitattributes` 仍然必须保留——它保护的是 Windows 那一侧。

## 参考文档

| 文件 | 内容 |
|---|---|
| `docs/annotation-guideline.md` | 标注规范（当前 v1），字段定义、证据规则、评测约定 |
| `docs/design-decisions.md` | 每个关键技术选择的备选方案、理由、已知代价 |
| `data/eval/hesitations.md` | 标注犹豫日志，修订规范的唯一依据 |
| `README.md` | 面向外部读者的项目说明、启动方式、截图 |
