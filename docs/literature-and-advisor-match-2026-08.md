# 文献阅读与谢倩倩导师匹配（2026-08）

## 结论先行

谢倩倩组的主线不是通用搜索引擎或纯 IR，但已经明确进入“检索 + 推理 + 事实性评测”：2025 年的
RAEmoLLM 使用检索到的跨域样本做 in-context learning，之后又有 Plan Then Retrieve 和 RAAR；FinCDM
则继续强调细粒度能力诊断。因此，本项目的 BM25/Dense/Hybrid/Rerank、证据覆盖、拒答和可复核评测
不是无人指导的旁支，最合适的定位是：**为她的垂域高风险生成与 agentic reasoning 补上可诊断、
可复现的 retrieval layer**。但如果把研究目标写成纯索引结构或检索模型训练，匹配度会下降。

武汉大学人工智能学院 2026 硕士口径为：`140500 智能科学与技术`（学术学位）和
`085410 人工智能`（专业学位），不能沿用计算机学院的专业名称与培养单位口径。

## 带着 `hesitations.md` 的四个问题读

1. multi-hop 应按必要的信息依赖，还是任一可行检索路径？
2. `out_of_scope` 怎样留下比“字符串无命中”更强的证据？
3. reasoning type 是否应随一次切块得到的 chunk 数变化？
4. 能否用某条基线的成功或失败反过来修改 gold label？

六篇文献共同支持的答案是：金标准应描述任务与证据关系，而不是某个实现的行为；需要把 retrieval、
generation、faithfulness 分层诊断；无答案与事实性判断需要可复核的人工协议或证据审计；数据构造还要
控制词汇重叠和 annotation selection bias，否则检索器比较会被数据生成方式污染。

## 第一组：导师核心论文

### FinBen: A Holistic Financial Benchmark for Large Language Models

来源：[arXiv](https://arxiv.org/abs/2402.12659)，NeurIPS 2024 Datasets and Benchmarks。
作者单位包含 The Fin AI、武汉大学、曼彻斯特大学及多所合作高校；谢倩倩为第一作者，论文列出的
武汉大学合作者与 Min Peng 团队说明她的金融 NLP 线有稳定的本地协作网络。

第一遍（问题—贡献—结论）：FinBen 最终版覆盖 42 个数据集、24 个金融任务和 8 个能力方面，并把
agent-based evaluation 与 RAG-based evaluation 纳入较完整的金融 LLM 评测。21 个模型的结果
表明：基础抽取/分析已较强，生成、预测、复杂推理仍弱，领域 instruction tuning 对复杂任务并不自动有效。

第二遍（方法与证据）：任务设计强调 broad coverage、真实应用、领域特征和人类认知能力；指标随任务
变化，而不是把所有能力压成一个分数。RAG 在这里是 benchmark spectrum 中的一部分，不是论文的主要
retriever 消融。该论文真正可迁移到本项目的是“分能力、分任务、保留可诊断指标”的评测观，而不是
直接复制它的金融数据或 aggregate score。

第三遍（局限与项目映射）：数据量、美国市场/英语偏置、模型规模与计算预算限制都影响外推；论文没有
系统回答 BM25/Dense/Hybrid 的检索层差异。套磁时应具体写：在 FinBen 的 holistic evaluation 思路上，
把 RAG 子系统拆成 evidence retrieval、complete evidence coverage、counter-evidence retrieval 和 refusal，
并以固定语料哈希及 offset gold spans 保证复现。这是对她 benchmark 主线的细化，不是泛称“大模型兴趣”。

### Factual Consistency Evaluation of Summarisation in the Era of Large Language Models

来源：[arXiv](https://arxiv.org/abs/2402.13758)，Expert Systems with Applications 254 (2024) 124456。
作者为 Zheheng Luo、Qianqian Xie、Sophia Ananiadou；论文首页将 Luo 与 Ananiadou 列为曼彻斯特大学，
将谢倩倩列为 The Fin AI。谢倩倩为通讯作者，并在贡献声明中参与 conceptualization、写作和 supervision。

第一遍：论文指出现有 factual consistency 评测集中在新闻，构建由循证医学专家标注的 TreatFact：
170 篇临床研究摘要及 ChatGPT/Vicuna 生成摘要；同时在新闻与临床域比较 11 个 LLM/传统指标。
专有模型在既有新闻 benchmark 上较强，但在 TreatFact 上所有方法基本接近 50% balanced-accuracy baseline。

第二遍：标注协议不是简单字符串匹配，而是检查 PICO、结论方向与 claim strength，并记录细粒度不一致；
实验比较模型规模、pre-training、fine-tuning、zero/few-shot 与 CoT。更大模型/更多预训练数据有帮助，
CoT 和 few-shot 不保证提升；高质量微调数据比提示技巧更关键。GPT 系列在 TreatFact 上有系统性
高估一致性的倾向，尤其会漏掉省略限定词导致的临床含义变化。

第三遍：这直接否定“让 LLM judge 替代 gold evidence 就够了”。本项目应保留人工 offset evidence、
counter-evidence 与拒答真值，把 RAGAS/LLM judge 当补充指标；`out_of_scope` 也必须保留同义词检索和
最相关候选人工排除记录。对导师匹配而言，项目的证据覆盖与拒答研究正对她的“高风险域事实准确性”，
而检索层比较提供了该论文未拆开的上游误差来源。

## 2025 年 5 月入职武汉大学后的产出核实

我按武汉大学主页给出的 Google Scholar ID `UYW7X_0AAAAJ` 定位作者记录，再用论文首页、ACM、
ACL Anthology 和 arXiv 逐条核对单位。完整清单与证据见 `docs/literature-notes.md`；套磁材料只能把
论文首页明确列武汉大学或正式作者记录能稳定归一的条目算作她的入职后产出。

- **RAEmoLLM**（ACL 2025）：检索情感相近的跨域示例用于 in-context learning，谢倩倩署名武汉大学。
- **Plan Then Retrieve**（WWW 2026）：学习何时查知识图谱、何时查 Web，正式出版页列武汉大学单位。
- **RAAR**（2026）：按语义、情感和写作风格检索多视角证据，再构造可验证推理路径。
- **MoodAngels**（NeurIPS 2025）：检索 DSM-5 条目和相似病例，作为高风险域 RAG 系统的旁证。
- **FinCDM、MultiFinBen、TaxPraBen**：延续细粒度能力诊断和垂域 benchmark 主线；其中 MultiFinBen
  论文首页仍列 The FinAI，套磁时不能笼统称为武大署名论文。

同名风险必须单独处理：DR³-Eval、Where Do Deep-Research Agents Go Wrong?/TELBench 和 TVIR 的
论文首页把 `Qianqian Xie` 列在南京大学/NJU-LINK 作者组，DR³-Eval 还给出南京大学学生邮箱。
在得到 ORCID、作者主页或本人确认前，这三篇不得归入武汉大学谢倩倩教授的成果。

判断：已经确认的 **RAEmoLLM → Plan Then Retrieve → RAAR** 足以证明她的研究进入检索增强与
agentic reasoning；最稳妥的套磁切口是为这条主线补充可诊断、可复现的 retrieval evaluation，
而不是借同名作者的 deep-research 工作夸大匹配度，也不要把自己写成要做传统 IR leaderboard。

## 第二组：RAG/IR 对照文献

### RAGAS

来源：[ACL Anthology](https://aclanthology.org/2024.eacl-demo.16/)。作者单位为 Exploding Gradients、
CardiffNLP（Cardiff University）及 AMPLYFI。

三遍摘要：第一遍确定其目标是无需人工 ground truth 的快速 RAG pipeline 评测；第二遍拆出 faithfulness、
answer relevance、context relevance/precision 等 LLM 驱动指标，并在 WikiEval 上看与人工 pairwise preference
的一致性；第三遍看到它适合快速迭代，却不能替代本项目的 evidence-span Recall/MRR/nDCG。原因是 judge
本身有模型/提示偏差，且“答案对上下文忠实”不等于“上下文召回了完整 gold evidence”。因此主报告用人工
gold retrieval metrics，RAGAS 只作为生成端补充与消融诊断。

### DomainRAG

来源：[arXiv](https://arxiv.org/abs/2406.05654)。作者单位为中国人民大学高瓴人工智能学院与百川智能。

三遍摘要：第一遍确定其用中国高校招生这一低资源、时效性垂域，构造 conversational、structural、
faithful、denoising、time-sensitive、multi-document 六种能力数据；第二遍比较 closed-book、gold reference、
retrieved reference，并用 EM/strict EM/F1/ROUGE-L/GPT-4 evaluation，发现闭卷明显失败、结构化 HTML 有益、
多文档与噪声场景困难，招生实体精确匹配下 BM25 可强于 BGE；第三遍看到它是**能力 benchmark**，不是
围绕固定技术文档语料做检索器与证据坐标的受控实验。

与本项目的区别必须能说清：DomainRAG 覆盖面更宽、中文招生域、包含对话/表格/时效/多文档；本项目更窄，
但冻结 revision、记录 Unicode offset gold evidence、隔离 BM25/Dense/Hybrid/Rerank/long-context/no-RAG，
并显式评 counter-evidence 和 out-of-scope refusal。它是竞品基准和设计参照，不是重复实现。

### BEIR

来源：[arXiv](https://arxiv.org/abs/2104.08663)，作者单位为 TU Darmstadt UKP Lab。

三遍摘要：第一遍确定其用 18 个异质数据集评估 lexical、sparse、dense、late interaction 和 reranking 的
zero-shot OOD 泛化；第二遍以 nDCG@10 为主并统一 corpus/query/qrels，发现 BM25 是稳健基线，reranking 与
late interaction 平均更强但成本更高，dense 并非处处胜出；第三遍关注 annotation selection bias：很多 qrels
由特定 lexical pool 形成，会对非词汇方法不利。对本项目的直接启示是必须保留 BM25，并在出题阶段控制
question–evidence lexical overlap，同时分层报告；否则结果可能只是标注/采样机制的产物。

### Self-RAG

来源：[OpenReview](https://openreview.net/forum?id=jbNjgmE0OP)，ICLR 2024 Oral。作者单位为 University of
Washington、Allen Institute for AI 与 IBM Research。

三遍摘要：第一遍确定它反对“无论是否需要都固定检索 K 篇”，让模型按需检索并自我反思；第二遍看到
retrieval/relevance/support/utility reflection tokens、离线 GPT-4 feedback→critic distillation、generator
联合预测文本与特殊 token，以及 segment-level decoding；第三遍看到代价是需要专门训练、teacher feedback
与复杂推理，并不等价于一个可直接套在任意 API 模型上的 prompt。对本项目最有价值的是把“是否需要检索、
证据是否相关、输出是否受支持”拆开测；但 30 题阶段不应把训练 Self-RAG 模型变成基础设施任务。

## 对标注规范 v1 的具体影响

- TreatFact 与 RAGAS：事实性 judge 只能是补充；人工证据与标注审计保留。
- DomainRAG：能力应分解，multi-document/denoising/faithfulness 不应压成一个最终答案分数。
- BEIR：新增固定词汇重叠度量、low/medium/high 配额与分层报告，控制 BM25 构造性优势。
- Self-RAG：reasoning type 描述证据依赖；是否检索、是否相关、是否受支持是不同变量。
- 四篇共同支持：不能用某次 BM25/Dense 结果反向修改 gold label。

## 时间账

8 月 T2 期末只安排论文阅读、导师匹配、规范和小型代码修订；剩余 25 题批量标注及完整实验安排到
9 月课程结束后。当前仓库不应因为基础设施顺利就提前扩大数据生产。
