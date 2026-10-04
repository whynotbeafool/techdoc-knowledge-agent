# Pilot 后范围审计与下一阶段入口

本次为同一已暴露主助手的探索性复核，不是独立裁决。原 QA、生成前审阅、响应审阅及 pilot LOCK 均保持不变；以下意见不进入原回放指标，也不据此补齐未知项或选择阈值。

| 项目 | 检查结果与后续处理 |
|---|---|
| q012 | 原清单将不暴露于 stack configuration 加入必要事实，超过题面“无需重建镜像更新机密配置”的要求。生成前已记录澄清，但发生在查看上下文之后，不能声称范围完全预注册。 |
| q015 | 可见示例将四空格称为额外一级缩进，另有 continuation lines 的四空格例外；缺少一般规则的直接句子。由示例推导普遍规范是范围敏感推断，原 true 保留，不能当作无争议的直接证据。 |
| q016 | 上下文出现 RAG-Sequence 名称、成绩和未命名的两种检索模式，但缺少名称与整段生成模式的明确对应。名称暗示不能替代证据，原 supported=false 保留。 |
| q020 | 题面要求 RL teacher 收集数据与突破 BC 上限；预先列为可选的蒸馏目标枚举不能在看到答案后升级为必需。 |
| q026 | 否定 Token 锁定单一来源并解释逐 token 使用不同文档，已覆盖题面核心。冻结清单额外要求 Sequence 对照，可能造成过严的 completeness 判定；原 false 不回改。新题应明确写出是否要求对照。 |
| q010 / q021 | 例外范围、延迟实验设置仍未解决；继续保留 null。不能用“需要阈值”作为填标签理由。 |
| 答案审阅顺序 | PROTOCOL.md 要求随机顺序；现有归档未提供可核验的随机呈现顺序记录。隐藏策略字段不足以证明落实随机化。本 pilot 不宣称符合该项要求；事后打乱记录不能恢复既往盲化。 |

下一阶段应在看见新生成结果之前，分别固定题面必要事实、允许替代证据、例外范围与呈现顺序。当前助手的复核不能替代独立审阅安排。

## 可执行的新题分组入口

新增 `scripts/prepare_question_groups.py`，调用 `app.evaluation.grouping.build_groups`：

- 对共享 necessary_fact_ids、parent_question_ids 和 prior_group_id 求传递闭包。
- 旧 q001–q030 即使被错误声明未暴露，仍强制进入 legacy-exposed-30；任何相连的新题随组进入 dev。
- 非旧组 ID 从排序后的成员 ID 完整 SHA-256 派生，再沿用协议 selective-v0.1 的分配规则。成员顺序不影响结果。题目重命名或增删成员会改变组 ID，因此必须先冻结成员，禁止为获得某一分配而修改它们。
- 缺失父题、重复 ID、空必要事实、缺失曝光声明会报错；输出以独占创建方式写入，拒绝覆盖原产物。

`next-dataset-20261004/candidates.jsonl` 是 4 道 PEP 8 草稿，覆盖 3 个声明的必要事实组。两道 imports 改写共享事实 ID；dunder 排序与字符串引号分别成组。每题附 canonical 原始字节哈希、字符区间和原文。尚未调用模型或开展检索调参。

`previously_exposed=false` 仅说明这些新题尚未观察系统输出，不表示作者未看过语料或旧 pilot。组清单明确为 provisional：尚需与完整旧题事实清单做语义重叠复核、跨文档扩充、完整性核查和最终冻结。**不得将草稿的 hash 分配当作已取得独立测试集。** 仅靠 fact ID 不同或原文区间不重叠无法证明独立；遗漏的语义联系不会被图算法自动发现。同文档共享及 AI 作者已暴露于旧 pilot 均为限制。

复现命令（输出必须使用不存在的新路径）：

```powershell
python scripts/prepare_question_groups.py --input research/next-dataset-20261004/candidates.jsonl --output provisional-groups-new.json
```

本轮远程生成调用为 0。既有 30 次调用额度已耗尽；新批次仍需完整配置、预检和预算安排。投稿版式继续后置。
