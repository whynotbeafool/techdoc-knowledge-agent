# 30 题冻结后的延迟自我复标计划

## 冻结信息

- 选定日期：2026-08-26
- 冻结文件：`data/eval/qa.jsonl`
- 记录数：30
- SHA-256：`21eb2747289309cb5c17fe0ea5b85744220b246a80f7b0314d430d72f847b975`
- 正式复标数量：14（46.7%）
- 统一最早复标日期：2026-09-09

从本文件建立起，首次 30 题实验及正式复标均以该哈希为输入。若因证据坐标错误等硬错误必须修订，
应先在 `hesitations.md` 记录原因，再更新哈希；不得根据任何 baseline 输出修改问题、答案或证据。

## 选择规则

未使用随机种子。采用预先声明的确定性分层选择：

1. 五种题类全部覆盖；single-evidence、multi-evidence、multi-hop 和 refuse 各取 3 题，
   correct-premise 取 2 题，共 14 题。
2. 11 道有证据题的词汇层为 low 3、medium 4、high 4，差值不超过 1。
3. 五份 active 语料全部覆盖；refuse 题按首个 `candidate_check` 计入审计覆盖，不把它当作 gold evidence。
4. q016/q017 已在 2026-08-26 做过提前的时间隔离裁决，因此排除在正式 14 题样本之外，
   避免把非预先抽样、已核对过首标的记录冒充盲化复标。
5. 统一等到最晚一批首标满 14 个自然日后再开始，避免分批复标造成不同的记忆间隔。

## 冻结的 14 题子集

| question_id | 类别 | 推理类型 | 词汇层 | 主要语料/审计候选 |
|---|---|---|---|---|
| q006 | answer | single_evidence | low | pep8 |
| q008 | answer | single_evidence | medium | fastapi_first_steps |
| q010 | answer | single_evidence | high | pep8 |
| q011 | answer | multi_evidence | low | fastapi_first_steps |
| q013 | answer | multi_evidence | medium | rag_paper |
| q014 | answer | multi_evidence | high | kubernetes_overview |
| q018 | answer | multi_hop | medium | rag_paper |
| q019 | answer | multi_hop | medium | autonomous_driving_survey |
| q020 | answer | multi_hop | high | autonomous_driving_survey |
| q021 | refuse | not_applicable | N/A | rag_paper |
| q023 | refuse | not_applicable | N/A | fastapi_first_steps |
| q025 | refuse | not_applicable | N/A | pep8 |
| q026 | correct_premise | single_evidence | low | rag_paper |
| q029 | correct_premise | single_evidence | high | kubernetes_overview |

## 执行纪律

复标时只向标注者提供冻结语料与上述题目的 `question`，隐藏首轮参考答案、证据偏移、人工维度标签、
`annotation_status` 和全部 baseline 输出。第二轮记录追加到 `data/eval/reannotation.jsonl`，不得覆盖
`qa.jsonl`。完成 14 题独立复标后，再按 §3.1 的五个人工维度核对差异并把裁决写入
`hesitations.md`。正式报告必须称为 intra-annotator temporal consistency，不得称为独立标注者一致性。
