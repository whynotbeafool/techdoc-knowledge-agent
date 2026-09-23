# 14 题复标：标注者入口

> 2026-09-23 修复：优先使用独立输入包 `D:/111求职准备/reannotation-blind-20260923-v2/START.md`。本仓库含首标与 baseline，不再作为盲标工作目录。旧入口保留作流程历史。新上下文仅解决输入隔离，不能证明首轮与次轮的标注者身份一致。

仅供未接触本次首标内容与实验输出的干净上下文使用。由当前主助手亲自标注；不委派，不让用户参与标注。

1. 先读取本目录 `questions.jsonl`，其中只有冻结 ID 和原问题。使用 `data/corpus/active-revisions.json`、`documents.jsonl` 及相应 canonical text；核验语料哈希。
2. 可读 `docs/annotation-guideline.md` 的通用规则。完成所有 14 题之前，不读 `reannotation-plan.md` 的分层表、`qa.jsonl` 内容、既有 `reannotation.jsonl` 内容、`hesitations.md`、论文、项目状态和 results。不要进行跨目录全文搜索。需要机械取元信息时，只输出哈希/日期，不输出标签或答案。
3. 按规范 §3.1 分别记录问题质量、语料支持类别、最小充分证据推理拓扑、英文参考答案充分性、证据/排除搜索充分性。自行选择证据位置；不得照预期配额猜标签。保留疑问及理由。派生字段随后机械计算。
4. 将 14 题第二轮完整记录先保存到独立文件并记录 SHA-256，校验 schema、证据坐标及引文。锁定全部判断后，才读取首标，逐维核对和裁决；不按答案字符串完全相等计算，不以整条完全一致代替五维结果。问题质量等首标未显式记录的判断应说明其回溯性质。
5. 通过后追加到 `data/eval/reannotation.jsonl`，保留历史行；裁决另记 `hesitations.md`，不覆盖首标，不因 baseline 调整真值。仅在身份连续性有依据时称 intra-annotator temporal consistency；无法确认则报告 AI reannotation consistency，披露与原计划的偏离、实际 AI 标注身份/版本及盲化边界，不声称独立人工双标。

该入口只准备了无标签材料，不代表已经完成正式复标，也不自动消除曾经暴露内容的记忆。
