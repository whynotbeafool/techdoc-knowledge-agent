# fix-report 核查修复记录 — 2026-09-23

修复基线：`c29a0f4`。本记录区分可修复的实现/报告错误与无法事后补造的实验独立性。此次改动完成本地及隔离导出验证后，按用户要求提交并推送；提交身份以 Git 历史为准。

## 保留的历史证据

- 冻结 `qa.jsonl` 的本地原始字节不变：`21eb2747289309cb5c17fe0ea5b85744220b246a80f7b0314d430d72f847b975`。
- 原计划、锁定输入、annotations、dimensions、LOCK、semantic-review、intake-receipt 和累计 reannotation 原文件未修改。
- 原检索/生成运行与 `results/audits/2026-09-23/` 未覆盖；没有付费生成调用，也未重跑生成响应。
- 来源 URL 元数据更新为已核实的 arXiv 版本；原 PDF source_hash、canonical text 和偏移不变。

## 逐项处理

| 条目 | 修复结果 |
|---|---|
| FIX-01 | 保留完整六题的真实数字，摘要、结果、讨论和合稿补上 q017 单题驱动与排除敏感性；不改成无条件三者并列。 |
| FIX-02 | 新增 frozen-inputs.json，严格认可原始哈希与 c29a0f4 的已核实 LF 序列化哈希。仅 7 个 CRLF 差异，拒绝任意其他字节变化；不重写历史 configs、计划或 LOCK。两道检查兼容干净检出。 |
| FIX-03 | 严格按检索 run_id、method、question_id 关联，并逐条核对 ranked list；拒绝缺失、重复和冲突记录。新条件单元为全体 15/9、confirmed-only 14/9；原主分数不变。未来 generation config/summary 均 schema 2，并报告缺失关联数和协议度量范围。 |
| FIX-04 | 补报有证据题拓扑 9/11、状态 13/14（κ=0）、答案字符串 3/14（全 null）；注明 D 是另一个 AI 任务的锁定后语义复核、E 是事后区间对应。日历延迟没有测量人类式记忆衰减，不能追认独立信度。 |
| FIX-05 | 统一引用页码格式：None、0、缺失值显示“页码不适用”；Chroma 新元数据不保存虚假零页，读取仍兼容历史零页。同步生成上下文、CLI 与 Streamlit。历史 23/30 输入受影响，结果未伪装成已重跑。 |
| FIX-06 | 保留原拒答前缀协议指标，正文与机器产物明确不是语义答案正确率；列出 q003/q027/q029 的纠正目标与前缀冲突。未使用关键词/长度规则人为消除假阳性。 |
| FIX-07 | 明确程序性隔离、非 OS 隔离、缺少独立外部见证；v2 输入副本已入库，v1 完整执行材料仍未入库，两次暴露尝试均排除。不能用哈希倒推未暴露。 |
| FIX-08 | A 标签改为 9/2/2/1 的实际分布；q016/q017 两轮日期有各自含义，未统一或改写。 |
| FIX-09 | QA 加入 -text；新增真实 QA/schema/坐标及冻结身份测试、active/sources 完整性快照。CI 显式运行 QA 与锁定复标检查。历史 LF 副本有明确例外，不作任意换行宽容。 |
| FIX-10 | 检查器补查 dimensions 题干、完整有效语料及正文、语义复核覆盖题号、接收凭据、历史两行前缀及累计追加记录。单独补建锁定后 review manifest，未修改原 LOCK，不声称外部认证。 |
| FIX-11 | 提交 rebuild_saved_audit.py，覆盖 5 个检索 run 和 1 个生成 run，附输入/输出哈希与差异解释。pilot-5 无可重算旧汇总，明确标记；pilot-9 的原 32 个单元全等，新代码增加分层元数据和单元。重建截断审计 JSON，并复查已保存的 90 行检索复现记录；不冒称本次重新运行了检索器。 |
| FIX-12 | README 去掉易过期的测试数量，明确覆盖率只报告 backend/app 且没有失败阈值；更新 CLAUDE 与 STATUS，保留历史验证记录的时间语境。 |
| FIX-13 | 明确 5 条有效语料与 6 条含历史清单的区别；固定直接依赖版本；拒绝危险上传文件名；生产检索路径使用上下文管理释放资源；BM25 的非正 top_k 与其他检索器一样返回空列表。RAG v4、综述 v3 的下载字节匹配冻结 source_hash 后固定链接；不猜测 v1。 |

## 可重复运行

```powershell
python scripts/validate_eval.py
python scripts/check_locked_reannotation.py --packet data/eval/reannotation-20260923/input --output-dir data/eval/reannotation-20260923
python scripts/rebuild_saved_audit.py --output-dir results/audits/<新的审计目录>
python -m ruff check .
python -m pytest tests/ -q -p no:cacheprovider --basetemp <新的可写临时目录>
```

新审计入口：`results/audits/2026-09-23-fixes/MANIFEST.json`。manifest 不哈希自身，也不是第三方见证。复跑时会实测当前文件字节；Windows/Git 旧序列化的实际哈希可不同，须结合 provenance 阅读。

## 实际验证

- Ruff：全部通过；git diff --check：通过。
- 当前工作区：181 passed。
- 隔离导出：从 HEAD 导出 tracked tree，叠加修复文件，在新临时目录将 QA 保持为旧 Git LF 字节（`1e9190…`），不使用原工作区的导入路径。QA、复标哈希检查、覆盖审计均通过，全套 181 passed。此项是本机隔离导出验证，不是远端 CI 或另一操作系统测试。
- 新审计 manifest 的全部输出哈希及生成脚本哈希复核一致。
- 截断：59/379（15.57%），未发现 gold evidence 落在被截掉的窗口。
- 低重叠：六题 ER@5 为 1/3、1/2、1/3；排除 q017 后五题均 0.4，Complete Hit@5 均 0.2。
- arXiv 版本来源核查详见 `data/corpus/source-version-verification-20260923.json`，两份完整 PDF 哈希均与冻结来源一致。

## 仍不能声称完成的事项

- 独立人工语义复核、人类延迟自我标注信度、历史未暴露的外部证明，都不能靠补代码产生。
- 依赖只固定了直接版本，没有完整的跨平台传递依赖锁；本轮未执行远端 Linux CI，也未做浏览器端交互验收。
- 原始 30 条生成输出没有在修正页码后重新生成，语义答案/引用质量仍未独立评分。
- 覆盖指标规范定稿、FinBen/RAGAS/Self-RAG 逐条溯源和投稿版式仍是后续研究任务，不混入本次修复完成声明。
