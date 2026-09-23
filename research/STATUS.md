# 项目实证盘点（2026-09-23）

范围：审阅科研深化指南、核对现有项目、修复 14 题复标的隔离入口。全文主张的依据限于当前仓库与本次本地运行，不包含文献全文新核查或付费生成调用。

## 仓库与环境

- 仓库：`https://github.com/whynotbeafool/techdoc-knowledge-agent.git`。
- 原盘点起点：`48dc9cf1bd4942ab34ba5dcd783aa540227c1800`；该盘点及归档已在 `c29a0f4` 提交并推送。下文原盘点命令与结果保留作为历史记录。
- Windows / Python 3.13.5；Chroma 1.5.9、pypdf 6.14.2、OpenAI Python 2.44.0、pytest 9.1.1、ruff 0.15.22。
- 起始工作区不干净：上次留下 `data/eval/hesitations.md`、`docs/paper/discussion.md`、`docs/paper/manuscript.md` 修改及 `data/eval/blind-reannotation/` 新目录，本次保留。这些起始变化已随 `c29a0f4` 提交并推送。
- 未发现适用 AGENTS.md；沿用已读取的 CLAUDE.md 约束。CLAUDE.md 的“30 题 baseline 尚未运行”等状态已过时，应以本盘点和原始产物为准。
- `backend/requirements.txt` 未固定版本；本次证明当前环境可运行，不证明新环境可精确重建。

## 本次实际验证

运行结果存放 `results/audits/2026-09-23/`，未覆盖任何历史 run。

| 检查 | 结果 | 证据 |
|---|---|---|
| 冻结 QA | 30 题、全部 dev；SHA-256 保持 `21eb2747289309cb5c17fe0ea5b85744220b246a80f7b0314d430d72f847b975` | `saved-artifact-checks.json` |
| schema / 坐标 / 引文 | 0 errors / 0 warnings | `python scripts/validate_eval.py` |
| 预定新增题配额 | 25/25；0 errors / 0 warnings | `python scripts/check_annotation_plan.py` |
| 三检索器重新运行 | 379 chunks、90 条逐题记录；除 run_id 外与 `frozen-30-hybrid-rrf-v1` 逐字段完全相同 | `audit-2026-09-23.*`、`reproduction-comparison.json` |
| 旧检索汇总重算 | 完全一致 | `saved-artifact-checks.json` |
| 旧生成行为分数重算 | 30 条逐题 metrics 与原有主汇总 cells 完全一致 | `reproduction-comparison.json` |
| 生成 summary 版本 | 原文件 schema 1；当前代码 schema 2 增加 retrieval_conditioned_cells，因此整个 JSON 不同，不是旧主分数漂移 | `generation-recomputed-summary.json` |
| 测试 | 156 passed | 下列 pytest 命令 |
| 静态检查 | All checks passed | `python -m ruff check .` |

初次 pytest 默认临时目录/缓存无写权限，产生 42 个 setup errors（114 passed），不作代码失败结论。改用工作区独立 basetemp 并关闭 cache provider 后全部通过；未改测试以掩盖失败。

```powershell
python scripts/validate_eval.py
python scripts/check_annotation_plan.py
python -m pytest tests/ -q -p no:cacheprovider --basetemp tmp/pytest-audit-20260923-0927 --tb=short
python -m ruff check .
python scripts/evaluate_retrieval.py --run-id audit-2026-09-23 --results-dir results/audits/2026-09-23
```

复现时为新运行选择未占用的 run-id 和结果目录；pytest basetemp 也使用新的空目录，不指向需保留的数据。原结果文件有防覆盖检查。

## 已存在的能力及其边界

- 语料：`data/corpus/` 的五份 active 文档、revision 与 SHA-256；证据坐标为 canonical text 的 Unicode 码点区间。
- 检索：`backend/app/evaluation/retrieval.py`、`scripts/evaluate_retrieval.py`；BM25、Dense、RRF 同输入可复现。confirmed answerable n=17，Recall@5 分别 .6471/.5588/.6471，Complete Hit@5 为 8/17、7/17、9/17；Hybrid 较早排名并非普遍较好。
- 生成：`scripts/evaluate_generation.py`、`results/generation/frozen-30-bm25-deepseek-v1.*`；存在 30 条真实响应记录，配置标记 deepseek-v4-flash、0 system errors。此处是存档事实，不是对供应商当前模型身份的外部核验，也不是本次重新调用结果。
- 行为：`backend/app/evaluation/behavior.py` 按响应开头的拒答标记分类；原 refusal accuracy .7000、precision .4000、recall 1.0000。只说明该响应协议，不能等同内容正确率或无依据回答率。
- 生成器调用输入为 question 与复原 chunks；离线评分读取 QA。当前不存在指南所需 B/C 门控，也没有运行时充分性特征管线。
- 原始生成文件保存响应、检索坐标、分数及行为指标；没有逐条费用、token usage、延迟、语义支持标签。context 可由冻结文档与坐标恢复，但原 prompt 只存哈希、当前提示词已修改。
- `audit_evidence_coverage.py` 与论文 coverage-audit 提供字符区间敏感性分析；完整证据接触、字符覆盖和语义充分性不能互换。没有必要事实/equivalent evidence groups 的新标注。
- `ChromaRetriever.describe()` 已为新 run 记录距离、index、模型声明信息与单位范数探针。`model_sha256` 来自库中的模型包校验常量，不应冒充逐文件实测哈希；历史 run 不倒填。
- 9 月 18 日 Limitations 已加入 59/379 chunks 超过 256-token 上限及 l2/cosine 差异。本次新 run 记录实际 l2、cosine 声明与单位范数探针。截断未覆盖已标 gold 的结论不排除排序影响。

## 14 题复标：已完成隔离 AI 第二轮及锁定后对照

当前会话曾暴露首标与 baseline，初版独立包的规范也夹带历史汇总；两次尝试均排除。初版任务的未锁定产物不用作正式样本，事件保存在 `data/eval/blind-reannotation/incident-20260923-package-v1.md`。

用户授权的替代任务“14 题独立复标执行”（`01a0c9f4-2374-77c3-82ff-333f3f0c6ffe`）只读取 v2 纯规则包。账户额度中断后在同一隔离上下文恢复，未传入任何首标或比较信息。该任务由主助手亲自完成，不使用子代理或用户标注，2026-09-23 13:12:15 Australia/Sydney 锁定，声明无禁止信息暴露。

本任务在锁定后复验输入/输出哈希、原问题、坐标和 schema，随后追加 14 条原始记录到 `data/eval/reannotation.jsonl`；原 q016/q017 两行保留，现共 16 行。首标 `qa.jsonl` 哈希不变。累积文件校验 0 errors、1 warning（q013 的完整句为 305 字符，理由已记录）。第二轮原始状态为 13 confirmed / 1 needs_review（q021）。

结果：B 支持类别 14/14 一致；C 拓扑 12/14 一致（补充 κ=0.8056）；D 必要成分 10/11 可确认一致；E 选定证据集双向定位对应 9/11，三个拒答审计结论一致。A 没有独立首轮标签，不能倒推一致率。q010 的答案范围仍待明确，q013 的另一句充分证据支持 single_evidence，q021 保留问题质量疑问；不将裁决回写两轮记录来提高一致率。

有效批次、LOCK、五维理由、语义核对、接收凭据及可移植输入包见 `data/eval/reannotation-20260923/`；执行时原包位于 `D:/111求职准备/reannotation-blind-20260923-v2/`。`scripts/check_locked_reannotation.py` 可重复核对，拒绝未锁定或被改动的产物。完整报告见 [REANNOTATION_REPORT.md](REANNOTATION_REPORT.md)。`saved-artifact-checks.json` 是追加前的审计快照，其中原复标 ID 列表只有两项不是当前累计数量。

原计划名称为 intra-annotator temporal consistency，但首标 `self` 缺少身份/模型版本证据；新的 AI 上下文不能证明同一人跨时间判断。结果按 AI reannotation consistency 报告，不能声称独立人工双标或已验证的人类时间一致性。输入隔离依赖新任务和读取纪律，并非操作系统访问封锁。执行与接收已完成，身份及问题范围限制仍需在正式研究结论中披露。

## 最小后续路线

1. 已完成：隔离 AI 第二轮、锁定与逐维对照；必需后续：明确 q010/q021 的范围和标注身份，保留原 gold 与偏离记录。
2. 必需：随后完成覆盖指标规范、FinBen/RAGAS/Self-RAG 原文逐条核查；明确是否采用指南提出的新主问题。
3. 新研究阶段必需：冻结版本化 A/B/C 协议、语义判定及分母，再分组构建新数据；开发集调阈值、保留集单次验证；运行同条件对比与关键组件消融。
4. 可选：迁移第二检索器、更大数据量、证据冲突类别。投稿模板排在实证结果之后。

本次不新增付费调用，不扩数据，不调整检索参数，不把审阅指南当作整套实验的执行授权。指南审阅及方法学冲突详见 [GUIDE_REVIEW.md](GUIDE_REVIEW.md)。


## fix-report 核查修复

本次修复保留冻结 QA、原计划、全部原始运行和 LOCK 覆盖的文件。哈希异常是 7 个 CRLF 的 Git 规范化，不是标签内容差异；兼容两个确证字节身份。新审计见 `results/audits/2026-09-23-fixes/`，可用 `python scripts/rebuild_saved_audit.py --output-dir <新目录>` 重建。

原审计的 retrieval_conditioned_cells 全空，不能视为已完成条件分析。补关联原检索记录后为 15/9（全体）与 14/9（confirmed-only）；不改历史生成分数。复标 A 标签、分母、事后复核边界与 q017 敏感性已补报。完整修复范围和验证见 `research/FIX_REPORT_RESOLUTION.md`。
