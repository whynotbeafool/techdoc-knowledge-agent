# 冻结 14 题复标：独立输入包

这是一轮由 AI 主助手亲自执行的第二轮证据标注。用户不参与标注，不使用子代理。输入限于本目录；不要访问任何旧任务或其他目录。这里没有首轮标签、首轮参考答案、首轮证据坐标或 baseline 输出。

## 执行

1. 读取 questions.jsonl（仅 question_id / question）及 guideline.md。核验 INPUT_MANIFEST.json 的文件哈希和 corpus/documents.jsonl 的语料 text_hash。所有问题保留原文，语料不可编辑。
2. 逐题按 guideline 的五个维度独立判断。写入 annotations.jsonl，使用 guideline 中的 v1 schema，annotator 如实记录为 codex_main_assistant，并记录实际当前日期。额外写 dimensions.jsonl：每题包含 A 问题质量判断及理由、B 语料支持判断及理由、C 推理拓扑及必要依赖理由、D 答案成分充分性及理由、E 证据/排除搜索充分性及理由；不确定性写 hesitations.md。不输出首轮一致率。
3. 所有答案与证据用英文；证据坐标为 Unicode 码点的零基半开区间。无答案题搜索全部五份语料并检查相关候选；字符串零命中不能代替语义核查。不得按猜测的配额分配题型。
4. 用本地脚本机械校验全部 14 条唯一 ID、问题原文、证据/候选引文切片、revision/page、字段组合与词汇重叠。词汇公式与固定停用词见 lexical-rule.json。人工语义判断由你完成，脚本不得自动生成答案或继承标签。
5. 完成全部判断与校验后，写 LOCK.json：annotations.jsonl、dimensions.jsonl、hesitations.md 的 SHA-256、实际时间、执行者可知身份、输入清单哈希和是否有暴露事件。锁定后停止编辑这些产物，不读取首标、不自行比较。外部核对阶段会检查结果并追加到原仓库。

## 报告边界

本次不得声称独立人工双标。当前包不证明首轮 self 字段对应的具体人或模型；首轮和第二轮标注者身份连续性需另行核对。若只能确认 AI 会话间重标，应称 AI reannotation consistency，并说明是否满足原计划的 intra-annotator temporal consistency 条件仍待审查。空上下文隔离不是人类遗忘间隔的实验等价物。

首标冻结 SHA-256：21eb2747289309cb5c17fe0ea5b85744220b246a80f7b0314d430d72f847b975。原计划最早启动日期 2026-09-09；不得据此推断每题类别。完成此包不自动完成首标比较及裁决。
