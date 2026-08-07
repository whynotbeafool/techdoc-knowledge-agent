# 剩余 25 题标注计划（v1）

> 机器可读的规范真值是 `data/eval/annotation-plan.json`；本文只保留配额的论证与人工说明。
> 标注进度以 `scripts/check_annotation_plan.py` 的输出为准，不在本文手工维护。
> 唯一编辑位置：当前 Desktop 仓库；同一时间不得在其他机器修改 `data/eval/qa.jsonl`。
> 全部新增记录固定使用 `schema_version: "0.3"`、`guideline_version: "1"`、`split: "dev"`。

## 1. 最终 30 题的题型配额

现有 q001--q005 每类各 1 题。剩余 25 题每类新增 5 题，冻结后每类各 6 题。

| 题类 | 现有 | 新增 | 最终 |
|---|---:|---:|---:|
| 单证据可答 | 1 | 5 | 6 |
| 多证据可答 | 1 | 5 | 6 |
| 多跳可答 | 1 | 5 | 6 |
| 明确无答案 | 1 | 5 | 6 |
| 错误前提 | 1 | 5 | 6 |
| 合计 | 5 | 25 | 30 |

最终构成为 18 道普通可答题、6 道明确无答案题、6 道错误前提题。30 题全部是 dev，结果只能
作为 pipeline 验证与初步实验，不得冒充 held-out test 结果。

## 2. 新增有证据题的词汇重叠配额

剩余 25 题中，20 题具有 gold evidence；low / medium / high 固定为 7 / 7 / 6。五道明确
无答案题的 `lexical_overlap` 为 `null`。

| 题类 | low | medium | high | N/A | 合计 |
|---|---:|---:|---:|---:|---:|
| 单证据可答 | 2 | 2 | 1 | 0 | 5 |
| 多证据可答 | 2 | 1 | 2 | 0 | 5 |
| 多跳可答 | 2 | 2 | 1 | 0 | 5 |
| 明确无答案 | 0 | 0 | 0 | 5 | 5 |
| 错误前提 | 1 | 2 | 2 | 0 | 5 |
| 合计 | 7 | 7 | 6 | 5 | 25 |

配额是构造约束，不是让题目迎合某条检索器。每题先按自然问题和最小充分证据定稿，再由校验器
计算实际分层；若未落入预定层，先尝试不删除关键实体的自然释义。仍无法自然达到目标时换题，
不得手改 `lexical_overlap.score` 或 `stratum`。

## 3. q006--q030 预分配

以下是方便人工阅读的镜像；若与 JSON 不一致，以 JSON 为准。

| question_id | reasoning_type | expected_behavior | 目标重叠层 |
|---|---|---|---|
| q006 | single_evidence | answer | low |
| q007 | single_evidence | answer | low |
| q008 | single_evidence | answer | medium |
| q009 | single_evidence | answer | medium |
| q010 | single_evidence | answer | high |
| q011 | multi_evidence | answer | low |
| q012 | multi_evidence | answer | low |
| q013 | multi_evidence | answer | medium |
| q014 | multi_evidence | answer | high |
| q015 | multi_evidence | answer | high |
| q016 | multi_hop | answer | low |
| q017 | multi_hop | answer | low |
| q018 | multi_hop | answer | medium |
| q019 | multi_hop | answer | medium |
| q020 | multi_hop | answer | high |
| q021 | not_applicable | refuse | N/A |
| q022 | not_applicable | refuse | N/A |
| q023 | not_applicable | refuse | N/A |
| q024 | not_applicable | refuse | N/A |
| q025 | not_applicable | refuse | N/A |
| q026 | null（按纠正所需证据填写） | correct_premise | low |
| q027 | null（按纠正所需证据填写） | correct_premise | medium |
| q028 | null（按纠正所需证据填写） | correct_premise | medium |
| q029 | null（按纠正所需证据填写） | correct_premise | high |
| q030 | null（按纠正所需证据填写） | correct_premise | high |

q026--q030 在计划中的 `reasoning_type: null` 表示**不预分配证据拓扑**，不是允许对应的
`qa.jsonl` 记录填 `null`；实际记录仍须按最小充分反证填写 `single_evidence`、
`multi_evidence` 或 `multi_hop`。

题号一旦写入 `qa.jsonl` 就不得复用或重排。候选题若失败，保留该题号槽位并更换候选内容；不要
把后续题号向前移动。

## 4. 语料覆盖与逐题流程

- 20 道新增有证据题应覆盖全部 5 份冻结文档；每份文档目标 3--5 题，若确因内容结构无法满足，
  在 `hesitations.md` 记录偏离原因。
- 五道明确无答案题的 `candidate_checks` 应尽量各以不同文档作为最相关候选的主要核查对象，
  但无答案判定始终针对整个冻结语料，而不是单篇文档。
- 同一种题型不得全部来自同一文档；多跳题尤其要避免只利用目录或标题字符串制造伪多跳。

每题按以下顺序执行：

1. 选定自然问题与候选证据，不查看新增题的 baseline 输出。
2. 依次检查问题质量、语料支持类别、证据推理拓扑、金答案充分性、证据充分性。
3. 写入派生的 `expected_behavior`，计算 `lexical_overlap`，确认落入 JSON 声明的目标层。
4. 追加一条 `qa.jsonl` 记录并立即依次运行 `python scripts/validate_eval.py` 和
   `python scripts/check_annotation_plan.py`；前者检查记录的内在合法性，后者检查对当前 30 题
   计划的符合性。不得积累多题后一次性修偏移。
5. 任一人工维度犹豫超过 10 秒，立即写入 `hesitations.md` 并使用 `needs_review`。
6. 以脚本打印的进度和下一个 pending 槽位为准；下一题开始前确认仍由本机独占编辑。

## 5. 配额变更规则

配额冻结后原则上不改。若某一题型与重叠层组合无法在当前语料中自然构造，先在
`hesitations.md` 记录失败候选、尝试过的自然释义及失败原因。只有在至少两个候选都失败后，
才允许调整同一题型内部的层级分配；调整后 low / medium / high 总数仍必须保持 7 / 7 / 6。
先更新 JSON 并通过计划自洽性检查，再在本文件追加理由与变更记录。不得根据 BM25、Dense 或
其他 baseline 的实际排名结果调整配额。
