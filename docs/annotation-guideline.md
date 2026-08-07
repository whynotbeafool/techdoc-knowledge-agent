# 评测集标注规范 v1

> **状态**：v1，已根据 5 题试标、首次 BM25/Dense 检索实验以及相关评测文献完成修订。
> 每条 QA 记录都携带 `guideline_version`，以便日后区分它是在哪一版规则下标注的。
> 已按 v0 标注并参与历史运行的 5 题不原地改写；后续新增题目使用 v1。

## 1. 目的与适用范围

本规范定义 TechDocKnowledgeAgent 研究评测集的标注方式。评测集用于回答两个研究问题：

- **RQ1**：BM25、Dense、Hybrid、Rerank、Long-context、no-RAG 在技术文档问答中的检索效果差异。
- **RQ3**：引用校验、证据覆盖与拒答机制能在多大程度上降低幻觉、提高可验证性。

因此标注必须同时支持两类计算：**检索指标**（Recall@K、MRR、nDCG，需要金标准证据位置）和
**拒答指标**（知识库外拒答准确率、错误拒答率，需要明确标注的无答案问题）。

**语言约定（已锁定）**：问题、参考答案、证据引文**一律使用英文**。
语料全部是英文文档，若用中文提问，BM25 因为没有词项重叠会近乎失效，
Dense 检索也受限于当前英文为主的 embedding 模型——那样 RQ1 比较的就不再是检索方法，
而是跨语言能力，结论无效。跨语言检索作为未来工作，不混入本评测集。

## 2. 数据分三层，互不混淆

```
data/corpus/documents.jsonl      文档层：冻结语料、哈希、page 映射（已建成，不在本规范范围）
data/eval/qa.jsonl               QA 层：本规范定义的金标准，人工标注，稳定不变
data/eval/excluded.jsonl         排除登记：因超出当前文本证据范围而未收录的问题
data/eval/hesitations.md         犹豫日志：标注时的判断困难，用于修订本规范
results/runs/*.jsonl             实验层：每次跑基线的输出，可反复变化
```

**金标准与实验结果必须分离**。qa.jsonl 是一次标定、版本固定的真值，
与任何系统实现无关；某条基线跑出来的检索结果、生成答案、延迟和成本一律写进 `results/runs/`。
两者混写会导致：跑多条基线时不知道往哪写、真值被系统输出污染而失去参照意义。

## 3. qa.jsonl 字段定义

一行一条 JSON 记录。

```json
{
  "schema_version": "0.3",
  "guideline_version": "1",
  "question_id": "q001",
  "question": "What are the main challenges in end-to-end autonomous driving?",
  "answerability": "answerable",
  "expected_behavior": "answer",
  "unanswerable_reason": null,
  "reasoning_type": "multi_evidence",
  "reference_answer": "Multimodal fusion, interpretability, causal confusion, robustness and world modelling.",
  "evidence": [
    {
      "evidence_id": "e001",
      "document_id": "autonomous_driving_survey",
      "revision": "v1",
      "page": 1,
      "start_char": 942,
      "end_char": 1092,
      "quote": "We delve into several critical challenges, including multi-modality, interpretability, causal confusion, robustness, and world models..."
    }
  ],
  "unanswerable_search": null,
  "lexical_overlap": {
    "metric": "question_content_token_recall_in_evidence",
    "score": 0.43,
    "stratum": "medium"
  },
  "annotation_status": "confirmed",
  "split": "dev",
  "annotator": "self",
  "created_at": "2026-07-28"
}
```

| 字段 | 取值 | 说明 |
|---|---|---|
| `schema_version` | `"0.3"` | v1 记录结构版本；新增无答案检索审计与词汇重叠分层字段 |
| `guideline_version` | `"1"` | 标注时依据的本规范版本；历史 5 题保留 `"0"` |
| `question_id` | `q001`、`q002`… | 稳定主键，**一旦分配不得复用或重排**。它是 qa.jsonl 与各条基线结果表 join 的依据 |
| `question` | 英文字符串 | 见 §5 各类问题的构造要求 |
| `answerability` | `answerable` \| `unanswerable` | 见 §4.1 |
| `expected_behavior` | `answer` \| `refuse` \| `correct_premise` | 系统应回答、拒答，还是指出并纠正错误前提 |
| `unanswerable_reason` | `out_of_scope` \| `false_premise` \| `null` | `answerable` 时必须为 `null`；`unanswerable` 时必须非空 |
| `reasoning_type` | `single_evidence` \| `multi_evidence` \| `multi_hop` \| `not_applicable` | `out_of_scope` 填 `not_applicable`；错误前提按纠正所需证据填写 |
| `reference_answer` | 英文字符串 \| `null` | 可答题写简洁答案；错误前提写纠正性回答；`out_of_scope` 填 `null` |
| `evidence` | 数组 | 普通可答题和错误前提至少 1 条；仅 `out_of_scope` 必须为空数组 |
| `unanswerable_search` | 对象 \| `null` | 仅 `out_of_scope` 必填，记录检索词及人工核查的最相关候选，见 §4.7 |
| `lexical_overlap` | 对象 \| `null` | 有证据题必填，用于按问题—证据词汇重叠度分层；`out_of_scope` 为 `null`，见 §5.1 |
| `annotation_status` | `confirmed` \| `needs_review` | 自己不确定时填 `needs_review`，不要勉强填 `confirmed` |
| `split` | `dev` | 见 §6.2。30 题阶段一律 `dev` |
| `annotator` | 字符串 | 目前只有 `self` |
| `created_at` | `YYYY-MM-DD` | 标注日期 |

### evidence 条目字段

| 字段 | 说明 |
|---|---|
| `evidence_id` | 该题内唯一，`e001` 起编 |
| `document_id` / `revision` | 必须与 `data/corpus/documents.jsonl` 中已冻结的某条记录完全一致 |
| `page` | 人工回查 PDF 时的入口。纯文本文档填 `null` |
| `start_char` / `end_char` | **canonical text 上的零基半开区间，单位是 Unicode 码点**（等价于 Python `str` 下标），不是 UTF-8 字节偏移，也不是字形簇 |
| `quote` | `canonical_text[start_char:end_char]` 的**精确副本**，用于人工校验和坐标漂移时重新定位 |

**不得使用 `chunk_id` 作为证据锚点**。`chunk_id` 里的序号依赖当时的切分参数，
一旦做 chunk 大小消融就会全部错位，标注即作废。这是本评测集全部坐标设计的起因。

## 4. 证据标注规则

### 4.1 answerable 的判定

**判定标准**：仅凭 canonical text 中的文字内容，一个熟悉该领域但未读过全文的人，
能否得出参考答案。能，则 `answerable`；不能，则 `unanswerable`。

注意判定的是**语料**能不能支持，不是**你自己**知不知道答案。
你从别处知道的知识不算数——那正是要检测的幻觉来源。

`answerability` 与系统的预期动作并不完全等价：普通可答题应回答；
语料完全不涉及的问题应拒答；带错误前提的问题虽不能按原问法作答，
但系统应利用反证指出并纠正前提，而不是只说"无法回答"。

约束如下：

| 情况 | `answerability` | `expected_behavior` | `reference_answer` | `evidence` |
|---|---|---|---|---|
| 普通可答 | `answerable` | `answer` | 非空 | 至少 1 条支持证据 |
| 语料外 | `unanswerable` | `refuse` | `null` | 空数组 |
| 错误前提 | `unanswerable` | `correct_premise` | 非空纠正 | 至少 1 条反证 |

### 4.2 什么算"支持"

一段文字构成证据，当且仅当它**直接陈述了参考答案中的某个成分**；
错误前提题中，直接证伪前提的文字也构成证据。以下不算：

- 只是提到了相关主题，但没有给出答案（例如问"有哪些挑战"，某段只说"挑战很多，见第 5 节"）
- 需要读者自行推断、计算或跨领域补全才能得到答案
- 仅在参考文献列表、目录、页眉页脚中出现的字符串匹配

### 4.3 引文摘多长

**下限**：必须包含足以独立判断"这段确实支持答案"的完整语义单元，通常是一个完整句子。
**建议上限**：不超过约 300 字符；超过时校验器给 warning，标注者必须检查是否应拆成多条证据。

不要为了"看起来完整"而把整段都摘进来，也不要摘半句话导致离开上下文无法判断。

### 4.4 多段文字都支持答案时

标注构成参考答案所需的**最小充分证据集**。其中每一段独立记为一条 evidence，
不要合并成一个跨越无关文字的大区间；不要求穷举全文中所有重复或等价表述。
v1 **不区分**"单独就足够"和"仅部分支持"——两者一律平等记录。

这个简化是有意的：区分需要额外的判断规则和标注成本，
而当前最大的风险是标注太慢导致实验开不了工，不是指标不够精细。
等 30 题跑完一轮实验、确认现有指标不够用时再考虑细化。

### 4.5 同一段文字在文档中多处出现

不要求穷举所有重复位置。选入最小充分证据集的引文若在全文重复，
以**实际选定的那一处**偏移为准；不得让 `find()` 默认返回的第一处替代人工选择。
不同题目选择了相同 quote 的不同位置是合法的。

### 4.6 证据必须可机械校验

标注完成后，以下两条必须成立，否则该条记录不合格：

```python
canonical_text[start_char:end_char] == quote          # 引文与偏移一致
0 <= start_char < end_char <= len(canonical_text)     # 区间合法
```

这两条会由校验脚本自动检查（见 §7）。

### 4.7 `out_of_scope` 必须留下可复核的检索审计

“字符串无命中”不是无答案的充分证据。每道 `out_of_scope` 题必须填写
`unanswerable_search`：

```json
{
  "searched_terms": ["etcd", "data at rest", "encryption", "cipher", "AES"],
  "candidate_checks": [
    {
      "document_id": "kubernetes_overview",
      "revision": "v1",
      "start_char": 4100,
      "end_char": 4250,
      "quote": "...",
      "reason_not_answer": "The passage discusses Secrets but not encryption at rest."
    }
  ]
}
```

- `searched_terms` 至少包含问题原词、常见缩写/全称，以及能合理预见的同义或上位词；
  不能只记录一个原字符串。
- 即使词项搜索完全无命中，也必须用语义检索或人工浏览检查至少一个最相关候选段落，
  并说明它为什么不能支持答案。
- `candidate_checks` 是“排除审计”，不是 gold evidence；它不参与 Recall@K 分母。
- 审计只能支持“按当前检索词与人工检查未发现答案”的操作性结论，不能声称逻辑上证明了不存在。

## 5. 五类问题的定义

试标阶段每类各标 1 题，共 5 题。

| 类别 | `answerability` | `expected_behavior` | `reasoning_type` | 构造要求 |
|---|---|---|---|---|
| 单证据可答 | `answerable` | `answer` | `single_evidence` | 答案由**一段**文字直接支持 |
| 多证据可答 | `answerable` | `answer` | `multi_evidence` | 答案的不同成分由**多段并列**文字支持，各段之间无推理依赖 |
| 跨章节多步 | `answerable` | `answer` | `multi_hop` | 第一处证据给出的中间实体、属性或取值，是组成最终答案时连接第二处证据所必需的；若每段各自直接支持并列答案成分、可任意顺序读取，则是 `multi_evidence` |
| 明确无答案 | `unanswerable` | `refuse` | `not_applicable` | 问题合理但语料完全不涉及。`unanswerable_reason` 填 `out_of_scope`，`reference_answer` 填 `null` |
| 前提错误 | `unanswerable` | `correct_premise` | 按纠正所需证据填写 | 问题内含语料可直接证伪的错误预设。记录反证并给出纠正性 `reference_answer` |

**关于"前提错误"**：例如询问某工具的一个它并不具备的特性、或把 A 的属性安在 B 上。
这类问题专门检验系统会不会顺着错误前提编造答案，是 RQ3 的重要样本。
理想输出是引用反证并纠正前提，不是无依据地继续回答，也不是笼统拒答。

**关于"版本冲突"**：当前语料每份文档只有一个快照，无法构造真实的版本冲突问题。
待日后向语料中加入同一文档的多个 revision 后再引入该类别。

`multi_hop` 判定看的是**最小充分证据集中的信息依赖**，不是某次检索实际走过的路径，
也不是“存在一种可以先搜 A 再搜 B 的路径”。如果问题文本本身已经给出了第二跳所需实体，
或两段只是并列补全答案，则不得标成 `multi_hop`。熟悉文档的人能否猜到第二处位置、某个基线
是否恰好漏召回一跳，都不得改变该真值。reasoning type 与 chunk 数量正交：多段证据即使在
`chunk_size=800` 时落入同一个 chunk，仍按其语义依赖标注。

### 5.1 问题—证据词汇重叠分层

RQ1 比较 BM25、Dense、Hybrid 与 Rerank，因此问题不能都照抄证据措辞。每个有证据题在定稿后
计算 `question_content_token_recall_in_evidence`：问题与全部 gold quote 均按小写
`[A-Za-z0-9_]+` 分词，去除校验代码中冻结的英语停用词；分数为“问题中不同内容词同时出现在
任一 gold quote 的比例”。固定分层如下：

- `low`：`score < 0.25`
- `medium`：`0.25 <= score < 0.50`
- `high`：`score >= 0.50`

后续 25 题采用**先定配额、再出题**：在其中所有有证据题中，low / medium / high 数量之差
不得超过 1；每种 reasoning type 也应尽量覆盖不止一个重叠层。若高重叠题过多，必须用自然的
释义重写问题，而不是删除领域关键实体；若低重叠题只能靠晦涩绕写获得，则换题。最终报告除
总体 Recall/MRR/nDCG 外，还要按该三层报告结果，避免数据构造阶段先验地偏向 BM25。

## 6. 评测约定

### 6.1 命中判定规则（影响 Recall@K 的定义）

一个 chunk 算作命中某条证据，当且仅当二者在 canonical text 上的区间有**任意正长度重叠**；
**仅边界接触不算命中**。由 `app.evaluation.evidence.evidence_span_hits_chunk()` 实现。

选择"任意重叠"而非"完整包含"，是因为它对 chunk 大小最不敏感：
做 chunk 参数消融时，"完整包含"会随着 chunk 变小而系统性地降低命中率，
从而引入与检索质量无关的伪差异。论文中报告主表时采用本规则并写明理由；
如需更严格的口径，可另算一份"完整包含"版本作为补充。

主指标定义为 **Evidence Recall@K**：

```
单题 Evidence Recall@K
= 被 top-K 中任一 chunk 命中的 gold evidence 数 / 该题 gold evidence 总数

数据集 Evidence Recall@K
= 所有 answerable 题单题 Recall@K 的宏平均
```

错误前提题的反证检索单独报告，不混入普通 answerable 题的主 Recall。
另可报告 `Complete Evidence Hit@K`：一道题的最小充分证据集是否全部被 top-K 覆盖。
v1 不把它作为唯一主指标，因为它会把"命中部分证据"和"完全没有命中"都压成 0。

`needs_review` 不静默丢弃，也不与 `confirmed` 混成一个无法解释的数字。每项报告指标同时给出：

1. **confirmed-only（保守主结果）**：只计算 `annotation_status=confirmed`；
2. **all-annotations（敏感性结果）**：纳入 `confirmed` 与 `needs_review`。

两者必须使用相同的题型过滤与宏平均方式，并同时报告分母题数。若两者差异改变方法排序，
结论必须标为不稳定并优先复核相关题目。错误前提题的 counter-evidence Recall 也采用同样双口径，
且对多道题取宏平均，禁止只读取第一条记录。

**注意**：chunk 并不完整覆盖 canonical text——段落之间被 trim 掉的空白字符不属于任何 chunk。
因此证据引文不应只包含空白，实践中正常引文不会遇到这个问题。

### 6.2 dev / test 划分政策

- **30 题阶段：全部标为 `dev`**。此阶段的实验结果只用于验证 pipeline 打通，
  在任何材料中都必须注明是"初步结果"，不得作为最终指标引用。
- **达到 100 题后**才切出真正的 held-out `test`，且 `test` 只在最后跑一次。

理由：调 chunk 大小、top-k、拒答阈值这些超参必须在 `dev` 上做。
如果在同一批题上调参又在同一批题上报结果，就是在测试集上调参，方法论上站不住。
而 30 题若按 1:2 划分，test 只有 20 题，报出的 Recall@5 置信区间大到无法支撑结论，
不如明确声明全部为 dev。

### 6.3 规模阶梯

| 阶段 | 数量 | 目的 |
|---|---|---|
| 试标 | 5 | 探测规范漏洞，修订为 v1 |
| v1 首批冻结 | 30 | 跑通端到端实验，全部为 dev |
| 第一版研究数据集 | 100 | 切出 dev/test，产出可报告的结果 |
| 扩展 | 300 | 仅在自动辅助标注和质量控制成熟后考虑 |

认真标的 100 题优于潦草的 300 题。100 已是博士规划中的下限，不必向 300 冲。

## 7. 标注流程

1. 从 `data/corpus/documents.jsonl` 中选定目标文档，用 `load_canonical_document()` 载入
   （会自动校验哈希），在 canonical text 上定位证据并读取偏移。
2. 按 §3 填写记录，追加进 `data/eval/qa.jsonl`。
3. 运行校验脚本（待实现）检查：schema 完整、偏移合法、`quote` 与偏移一致、
   `document_id@revision` 存在于语料、三类 `expected_behavior` 的字段组合合法、
   `question_id` 无重复。引文超过 300 字符只给 warning，不作为失败。
4. **凡是判断时犹豫超过 10 秒的，一律记入 `data/eval/hesitations.md`**，格式：

   ```
   ## q003
   - 问题：引文该摘到句号还是摘完整段？
   - 当时的选择：摘到句号
   - 犹豫原因：后半段补充了限定条件，单看前半句可能被误解
   - 是否需要新增规范条款：是 —— §4.3 需要说明"限定条件必须包含在引文内"
   ```

   这份日志是修订 v1 的唯一依据。**不记录 = 规范永远修不对**。

### 7.1 超出 v1 范围的问题：排除并登记

v1 **只收录能够完全由 canonical text 支持的问题**。依赖图片、复杂表格或视觉排版的问题
一律排除，并登记进 `data/eval/excluded.jsonl`：

```json
{"question": "...", "reason": "evidence_is_figure", "document_id": "rag_paper", "page": 4}
```

`reason` 取值：`evidence_is_figure` | `evidence_is_table` | `needs_layout` | `other`。

这样做的目的：避免前 5 题就把 schema 撑成多模态标注标准（bbox、单元格坐标、OCR 字段）。
登记下来的问题有两个用途——论文 Limitations 一节的实据，以及后续扩展
`evidence_type: text | table | figure` 时的现成素材。

## 8. 五题试标后的决议

1. 300 字符保留为 warning 阈值，不作为硬失败；完整语义与必要限定条件优先。
2. “直接陈述答案成分”在当前纯文本语料中可操作，继续作为支持判据。
3. 四种 `reasoning_type` 暂时足够；§5 已把 `multi_hop` 收紧为最小充分证据集中的必要依赖，
   并明确其与一次切块得到几个 chunk 无关。
4. `unanswerable_reason` 暂不扩展；`out_of_scope` 改由 §4.7 的检索审计提高可复核性。
5. `expected_behavior` 的三分法保留；错误前提题继续单独报告 counter-evidence retrieval。
6. `needs_review` 采用双口径报告；基线结果不得反向污染金标准。
7. 为避免 BM25 获得构造性优势，新增 §5.1 的固定词汇重叠分层与配额。

## 9. 批量标注启动门槛

剩余 25 题开始标注前必须满足：

- [x] 校验脚本对 5 条记录全部通过
- [x] `quote` 与 `start_char/end_char` 能双向核对
- [x] 能用这 5 题跑出 BM25 与 Dense 的 Recall@K（数值无意义，只验证链路通）
- [ ] `answerable` 与 `unanswerable` 两类能分别算出拒答相关指标
- [x] `hesitations.md` 中的每一条都已转化为 v1 的修订项或明确判定为无需修订
- [x] `needs_review`、无答案检索审计、词汇重叠分层均已形成可执行条款
- [x] 校验器已能验证 v0 历史记录与 v1 新记录，且 v1 专属字段可机械复算
- [ ] 先建立剩余题目的 low / medium / high 配额表，再开始逐题标注
