# 文献笔记

更新时间：2026-08-07

本文件记录可直接进入 related work、标注设计和套磁材料的判断。论文内容以正式论文或作者提供的
公开版本为准；作者任职以院校官方主页为准。以下“能抄什么”指可迁移的研究设计，不指照搬文本、
数据或结论。

## 谢倩倩：两篇核心论文

### FinBen: A Holistic Financial Benchmark for Large Language Models

来源：[NeurIPS 2024 论文页](https://proceedings.neurips.cc/paper_files/paper/2024/hash/adb1d9fa8be4576d28703b396b82ba1b-Abstract-Datasets_and_Benchmarks_Track.html)，
[正式 PDF](https://proceedings.neurips.cc/paper_files/paper/2024/file/adb1d9fa8be4576d28703b396b82ba1b-Paper-Datasets_and_Benchmarks_Track.pdf)。

作者单位：正式版将谢倩倩同时列为武汉大学与 The Fin AI；其余作者来自武汉大学、曼彻斯特大学、
佛罗里达大学、哥伦比亚大学等机构。论文发表于 NeurIPS 2024 Datasets and Benchmarks Track。

事实摘录：最终版包含 42 个数据集、24 个金融任务和 8 个能力方面，评测 21 个模型。论文将 agent-based
evaluation 和 RAG-based evaluation 列为创新；新建的 Regulations 数据集含 254 个长答案 QA，问题映射到
EMIR 等法规条款，报告指标为 ROUGE 和 BERTScore。

- **能抄什么**：沿用“先分解能力、再为各能力选择可诊断指标”的评测观，而不是把不同失败模式压成一个
  总分。本项目可把技术文档 RAG 分解为单证据、多证据、多跳、拒答和错误前提，并分别报告检索覆盖、
  首个相关证据排名和生成端证据支持；同时保留任务级样本数，避免总体均值掩盖短板。

- **和我差在哪**：FinBen 是宽覆盖的金融 LLM 能力基准，重点是跨任务、跨数据集和跨模型的端到端表现；
  本项目是窄而受控的检索实验，冻结 5 份技术文档，以 Unicode 字符偏移标注 gold evidence，直接比较
  BM25、Dense、Hybrid、Rerank 等检索方法，并单独处理完整证据覆盖、反证和 out-of-scope refusal。

- **它没解决什么**：正式 PDF 中 RAG 只在摘要和引言的创新声明出现；任务定义、实验设置和结果没有给出
  独立的 retriever 配置、BM25/Dense 对照、Recall@K/MRR 或 gold evidence-span 评测。Regulations 的结果
  仍是答案级 ROUGE/BERTScore。因此它说明“金融评测应包含 RAG”，但没有诊断检索层为何成功或失败；
  这正是本项目 related work 的落点，而不是声称重复 FinBen 的 holistic benchmark。

### Factual Consistency Evaluation of Summarisation in the Era of Large Language Models

来源：[arXiv 论文页](https://arxiv.org/abs/2402.13758)，
[论文 PDF（含 Appendix F）](https://arxiv.org/pdf/2402.13758)，
[期刊 DOI](https://doi.org/10.1016/j.eswa.2024.124456)。

作者单位：论文首页将 Zheheng Luo、Sophia Ananiadou 列为曼彻斯特大学，将谢倩倩列为 The Fin AI；
谢倩倩是通讯作者，并在 CRediT 声明中承担 conceptualization、写作与 supervision。不能把这篇论文的
谢倩倩单位写成武汉大学或曼彻斯特大学。

事实摘录：TreatFact 由 85 篇临床研究摘要分别经 ChatGPT 和 Vicuna 生成 170 份摘要；4 名循证医学专家
按 PICO、结论方向、主张强度及其他不一致进行标注，并给 0–3 的总体事实一致性分。78/170 份摘要双标，
即 45.9%（可写约 46%）。分维度一致度为 0.73–0.94，而总体分一致度只有 0.55。由于标签不平衡，自动
方法使用 balanced accuracy；TreatFact 上各方法大多约为 50%，最佳表中结果也只有 52.1%。

- **能抄什么**：把复杂判断拆成可观察维度，并为一部分样本做独立复标。0.94 到 0.55 的落差直接支持
  本项目拒绝“单一总判断”，改用 `reasoning_type`、`expected_behavior`、证据集合和分层属性分别记录；
  78/170 的双标比例也为本项目的隔时重标/他人复标及 limitation 提供了可引用的先例。论文因类别不平衡
  选择 balanced accuracy，同样提醒本项目不能只看一个容易饱和或受分布支配的汇总数。

- **和我差在哪**：TreatFact 判断的是“给定源摘要时，生成摘要是否事实一致”，没有检索环节；其金标准
  是临床摘要的 PICO、方向、强度和总体分。本项目判断的是“固定技术文档语料中，系统是否先检索到完整
  gold evidence，再据此回答、拒答或纠正前提”，分析单位是 QA 与证据字符区间，而不是文档—摘要对。

- **它没解决什么**：论文证明现有 QA/NLI 指标和 LLM judge 在临床域接近随机基线，却没有评估上游检索、
  首个相关证据排名、多证据覆盖、引用坐标或拒答。因此它能支持“不能用 LLM judge 代替人工 gold”，
  但不能回答 BM25/Dense/Hybrid 谁更能找全证据，也不能区分检索失败与拿到证据后的生成失败。本项目以
  冻结语料、offset gold spans 和检索/生成分层评测补这个缺口。

## 2025 年 5 月入职武汉大学后的公开产出核查

### 身份与核查口径

[武汉大学教师主页](https://jszy.whu.edu.cn/xieqianqian/zh_CN/index.htm)记载：谢倩倩自 2025 年 5 月起任
武汉大学人工智能学院教授，现任语言与信息中心副主任。以下仅把满足至少一项的条目归入“已确认”：

1. 论文首页明确列出 School of Artificial Intelligence / Center for Language and Information Research,
   Wuhan University，或使用 `xieq@whu.edu.cn`；
2. ACL Anthology 的[谢倩倩作者页](https://aclanthology.org/people/qianqian-xie/)将论文归入同一作者记录，
   且合作者、主题与已确认记录一致；
3. ACM 等正式出版页明确给出武汉大学单位和同一 ORCID。

“公开时间在入职后”不等于“工作全部在武汉大学完成”；套磁材料必须按论文首页写单位，不能把 The Fin AI
或其他机构的署名自动改写成武大成果。

### 与本项目最相关、已确认的产出

| 公开/出版时间 | 论文 | 一手证据与单位 | 与本项目的关系 |
|---|---|---|---|
| 2025-06 | [MoodAngels](https://arxiv.org/abs/2506.03750) | PDF 将谢倩倩列为武汉大学人工智能学院、语言与信息中心；NeurIPS 2025 | 用 BGE-M3 检索 DSM-5 条目和相似病例，再由多 agent 诊断；说明她已直接做检索增强的高风险域系统 |
| 2025-07 | [RAEmoLLM](https://aclanthology.org/2025.acl-long.806/) | ACL 2025 正式论文；PDF 将谢倩倩列为武汉大学人工智能学院 | 用情感表示检索跨域示例作 ICL；有检索模块与 top-K，但主指标仍是误信息分类的 Accuracy/Precision/Recall/F1 |
| 2025-08 | [From Scores to Skills / FinCDM](https://arxiv.org/abs/2508.13491) | PDF 将谢倩倩列为武汉大学人工智能学院、语言与信息中心，通讯邮箱为 `xieq@whu.edu.cn` | 反对单一总分，以细粒度知识—技能诊断模型揭示同分模型的不同短板；与本项目的分层 cells 设计高度同向 |
| 2025-10；2026-04 正式出版 | [Plan Then Retrieve](https://doi.org/10.1145/3774904.3792191) | ACM WWW 2026 正式页列武汉大学人工智能学院、语言与信息中心及 ORCID；通讯作者 | 在不完整知识图谱下学习何时查 KG、何时查 Web，并显式优化规划与检索调度；证明她的研究已进入 retrieval planning，而非只做 benchmark |
| 2026-01 | [RAAR](https://arxiv.org/abs/2601.04853) | PDF 将谢倩倩列为武汉大学人工智能学院、语言与信息中心，通讯邮箱为 `xieq@whu.edu.cn` | 从源域按语义、情感和写作风格检索多视角证据，再构造可验证推理路径；延续 RAEmoLLM 到 agentic reasoning |
| 2026-07 | [MultiFinBen](https://aclanthology.org/2026.acl-long.770/) | ACL 2026 正式论文和作者页确认作者身份；论文首页把谢倩倩列为 The FinAI，而非武汉大学 | 把 FinBen 扩到五语言、文本/视觉/音频和难度感知选择；强化其垂域 benchmark 主线，但套磁时不能称为武大署名论文 |
| 2026-07 | [TaxPraBen](https://aclanthology.org/2026.acl-long.1765/) | ACL 2026 正式 PDF 将谢倩倩列为 Wuhan University | 将中文税务任务按记忆、理解、应用分层，结合结构化输出与人工验证；再次支持“能力分解而非总体平均” |

ACL Anthology 的同一作者页还列出 2026 年的 ClinicalSkillQA、EmCellLLM 和 Human or LLM as
Standardized Patients 等医疗评测工作。它们能证明“高风险垂域 benchmark/评测”仍是持续主线，但与当前
技术文档检索课题的直接关系弱，写套磁材料前应再读各自 PDF，而不是只凭标题扩写贡献。

### 同名作者风险：目前不得归入谢倩倩教授

arXiv 以作者名 `Qianqian Xie` 检索会混入至少一位南京大学/NJU-LINK 的同名作者。下列论文首页没有武汉
大学单位，反而把 Qianqian Xie 列在南京大学作者组或给出南京大学学生邮箱；在获得 ORCID、作者主页或
本人确认前，不得作为谢倩倩教授的产出写入套磁材料：

- [DR³-Eval](https://arxiv.org/abs/2604.14683)：论文首页列 Nanjing University、M-A-P、Jiutian Research
  等单位，并给出 `xieqianqian@smail.nju.edu.cn`；
- [Where Do Deep-Research Agents Go Wrong? / TELBench](https://arxiv.org/abs/2606.02060)：论文首页将
  Qianqian Xie 列在 NJU-LINK Team, Nanjing University；
- [TVIR](https://arxiv.org/abs/2606.02320)：论文首页作者单位为 Nanjing University 与 Alibaba Group。

因此，当前可以稳妥写入套磁材料的检索链条是 **RAEmoLLM → Plan Then Retrieve → RAAR**，旁证为
**MoodAngels**；评测链条是 **FinBen → FinCDM → MultiFinBen / TaxPraBen**。DR³-Eval、TELBench 和 TVIR
除非后续完成身份交叉核实，否则只能作为领域相关工作阅读，不能用于论证导师本人已经做过这些工作。
