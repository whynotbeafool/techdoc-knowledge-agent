# FinBen / RAGAS / Self-RAG 逐条溯源核查

日期：2026-09-28。范围：当前 related-work 中三篇论文的实际论断及其对覆盖规范的影响；不是全领域查新，也不代表其他引用已重新全文核验。下述内容均为转述。“不支持”项列出需要排除的推论，不表示旧稿已经写出了这些错误论断。定位使用论文印刷页码（从 1 起；RAGAS 同时注明出版页码）。

## 版本与访问记录

| 论文 | 本次使用的一手来源 | 实际核查位置 |
|---|---|---|
| FinBen | [NeurIPS 2024 正式论文](https://papers.nips.cc/paper/2024/file/adb1d9fa8be4576d28703b396b82ba1b-Paper-Datasets_and_Benchmarks_Track.pdf) | 摘要；§2.2 p4；§2.3 pp4–6，含 Table 2；不使用早期预印本的规模替代正式版 |
| RAGAs | [EACL 2024 正式论文](https://aclanthology.org/2024.eacl-demo.16.pdf) | §3 pp151–153；§4 pp153–154；§5/Table 4 p155；区分 2024 论文与后续软件接口 |
| Self-RAG | [ICLR 2024 正式论文](https://proceedings.iclr.cc/paper_files/paper/2024/file/25f7be9694d7b32d5cc670927b8091e1-Paper-Conference.pdf) | Table 1/§3.1 p3；§3.2 pp4–5；§3.3 pp5–6 |

OpenReview 本次返回浏览器验证页；已改用 ICLR 官方 proceedings 全文完成核查。arXiv 2310.11511v1 是 2023 预印本，只作为交叉查找，不冒充正式会议版本。references.bib 的 Self-RAG 链接改向可访问的会议来源。

## FinBen

| ID | 论断或需排除的推论 | 证据定位与结论 |
|---|---|---|
| F1 | 42 datasets / 24 tasks / eight aspects | 正式版摘要与引言支持；保留。 |
| F2 | Regulations 使用答案层面指标 | §2.3 Question Answering，p6：ROUGE 与 BERTScore；将模糊的“answer-level metrics”明确为这两项。 |
| F3 | 本项目与它的区别是证据坐标诊断 | §2.2 p4 说明 Regulations 的 QA 对与法规条款存在映射；不能写成 FinBen 完全没有证据或来源关联。本项目的字符级独立 gold 与固定检索器比较是本地设计差异，不是原论文声称的排他性。 |

设计影响：借鉴任务分解；不能据答案相似度推断完整证据覆盖，也不能凭此宣称本项目优于 FinBen。

## RAGAS

| ID | 论断或需排除的推论 | 证据定位与结论 |
|---|---|---|
| R1 | reference-free 的三类指标 | §3 pp151–153 支持 faithfulness、answer relevance、context relevance；措辞限定为该论文版本。 |
| R2 | faithfulness 检查回答受到上下文支持 | §3 p152：拆分陈述并由 LLM 判断支持，统计支持比例。不是与 gold answer 的字符串匹配。 |
| R3 | context relevance 等同全部必要证据召回 | **不支持。** §3 Eq.(2) p153 的分母是上下文句子数，不是独立标注的必要事实数。 |
| R4 | reference-free 意味完全没有人工评估 | **不支持。** §4 WikiEval 使用人工比较；§5/Table 4 报告与人工偏好的一致情况。reference-free 指计算这些指标不依赖参考答案，不是否定验证环节。 |

设计影响：可把自动语义判断作为代理信号；不能以该论文证明本项目的上下文充分性标签已获得验证。

## Self-RAG

| ID | 论断或需排除的推论 | 证据定位与结论 |
|---|---|---|
| S1 | 四类 reflection token | Table 1 p3 支持 Retrieve、ISREL、ISSUP、ISUSE；分别对应检索决策、相关性、生成内容支持、效用。 |
| S2 | 它是训练与生成框架 | §3.2 的 critic/训练数据增广和 generator 训练、§3.3 的解码控制支持；不是只给通用模型加一段提示词。 |
| S3 | ISSUP 是生成前的必要证据覆盖判定 | **不支持。** Table 1 输入含输出 y；判断生成片段是否被文档支持，与回答前所需全部事实是否齐备不同。 |
| S4 | 不触发检索等于拒答 | **不支持。** §3.1 不检索分支仍可继续生成；不能把其检索频率直接当作回答覆盖率。 |

设计影响：可借鉴相关性与生成支持的分离，不把本项目尚未实现的门控称为 Self-RAG 复现，也不把其结果移植成当前系统效果。

## 修改与边界

本轮更新 related-work 的 F2/F3、R1/R4、S2/S3/S4，并在对应论断旁加入章节定位；同步合稿。三篇论文均未被用于证明当前检索接触率等于语义充分性。上述“不等同”属于对定义的比较和本项目方法学判断，不声称已经审查其全部数据或代码。

DomainRAG、BEIR、TreatFact 和新增选择性回答文献不在这次三篇核查范围。下一阶段若改变主问题，需扩展文献集合并冻结新实验协议；不能将本表当作已完成所有新颖性审查。
