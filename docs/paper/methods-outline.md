# Methods 写作骨架

核对日期：2026-09-10。本文是写作依据，不是已完成的论文正文。
沿用先写初稿、再审阅的协作方式；先完成 §1，再逐节推进。

## 1. Frozen Corpus and Evidence Coordinates

建议正文 180–230 个英文词，按以下因果顺序组织，语料明细可放表格而不挤入正文。

1. **研究边界**：固定五份英文技术文档，包含研究论文和软件文档；问题与参考答案同为英文。
   这是小规模受控语料，不能称为代表整个技术文档领域的随机样本。
2. **固定比较对象**：源文件经提取成为 canonical text；记录源文件和规范文本的 SHA-256、提取工具版本、
   规范化规则与页区间。每个文档由 active 清单选择一个 revision，历史记录不等于本次索引成员。
3. **定义证据对象**：`e = (document_id, revision, start, end)`，区间为规范文本上的 `[start, end)`，
   单位是 Unicode 码点。`quote` 必须精确等于该区间的文本；PDF 页码仅辅助人工回查。
4. **解释为何这样定义**：证据不绑定 chunk 编号，所以改变切块参数不需要重标原文证据。
   但原文或提取流程改变了 canonical text 就必须新增 revision，旧坐标不能直接迁移。
5. **写明实际边界**：chunk 是原文的精确连续切片、不跨 PDF 页；它们并非覆盖原文每个字符，
   一些被裁掉的空白及页间分隔符不进入 chunk。坐标准确也不等于 PDF 提取语义完整。

### 已核对的语料表

| document_id | active revision | 来源类型 | canonical 码点数 | PDF 页数 |
|---|---|---|---:|---:|
| rag_paper | v1 | 研究论文 PDF | 69,094 | 19 |
| autonomous_driving_survey | v1 | 综述 PDF | 122,961 | 20 |
| fastapi_first_steps | v1 | Markdown 文档 | 13,704 | 不适用 |
| kubernetes_overview | v1 | Markdown 文档 | 10,501 | 不适用 |
| pep8 | v2 | 官方 PEP 仓库 RST 文本，以 .txt 导入 | 50,782 | 不适用 |

长度取自 manifest 最后一个 page span 的 `end_char`，包括文内空白和页间分隔符；不是 token 数。
PEP 8 的 v1 是历史错误页，不计入 active 语料。

### 实现与元数据依据

- `../../data/corpus/active-revisions.json`：本次语料成员及 revision。
- `../../data/corpus/documents.jsonl`：源文件/文本哈希、提取规则、页区间；PDF 提取使用 pypdf 6.14.2。
- `../../backend/app/corpus/canonical.py`：NFC 规范化、UTF-8 存储、revision 不可变性和 active 选择。
- `../../backend/app/rag/chunker.py`：chunk 切片和页边界规则。
- `../annotation-guideline.md` §3：证据偏移与 quote 约定。
- `../design-decisions.md` #11–12：不完整覆盖与历史 revision 的处理。

NFC 是提取后、标注前的处理；不要写成“源文件未经任何变换直接用于标注”。
暂不在这一节报告 chunk 数或大小；这些参数属于实验配置，需要绑定具体 run。

## 2. Question Construction and Annotation

写清五个人工判断维度、最小充分证据、必要依赖的 multi-hop 定义、三类预期行为。
`expected_behavior` 是支持类别的派生字段，词汇重叠是机械计算值；二者不是独立人工判断。
无答案题要记录同义词与候选排除审计，不能以字符串无命中证明语料无答案。
交代 30 题 dev-only、历史规范版本、复标覆盖规则与单人标注限制。

## 3. Lexical Stratification and Quality Control

从代码核对词项处理、重叠度公式与阈值，再写 low/medium/high 配额。
证据拓扑与词汇重叠是分别报告的边际轴，不叉乘；无证据题不强塞词汇层。
区分 baseline-independent evidence annotation 和对问题措辞的偏差控制。
复标已到计划执行日期，但时间经过不等于完成；须查实际复标记录再写样本数和一致性。

## 4. Retrieval Systems and Experimental Controls

根据具体 config 写 BM25、Dense、Hybrid 的模型与参数、同一切块输入、候选深度、排序融合及运行版本。
仓库已有 Hybrid 和生成评测代码；代码存在不等于已完成可报告的实验。
Rerank、Long-context、no-RAG 是否纳入需核对产物；后两者不能被笼统当作具有相同排序指标的检索器。

## 5. Metrics and Reporting

对照实现定义 evidence 命中、Evidence Recall@K、完整证据命中率及 MRR；尤其明确跨 chunk 覆盖规则。
分别写普通回答、反证检索与拒答的适用分母。
同时报告 confirmed_only 与 all_annotations，各 cell 给 n；不把小样本差异写成普遍优势。
生成行为、引用支持与检索覆盖分开定义；仅写实际已验证的指标。

## 第一节提交前自查

- 是否回答了“原文与 chunk 都会变化，为什么 gold 仍可比较”？
- 是否区分 Unicode 码点、UTF-8 字节、token 和 PDF 页码？
- 是否写清 revision 的稳定范围，而非宣称坐标永远稳定？
- 是否避免宣称所有字符都进入 chunk、提取内容完整或语料有代表性？
- 是否把本节维持为语料与坐标定义，没有提前塞进所有检索参数与实验结果？
