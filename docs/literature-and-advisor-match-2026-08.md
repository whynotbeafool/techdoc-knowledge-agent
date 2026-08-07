# 文献阅读与谢倩倩导师匹配（2026-08）

## 结论先行

谢倩倩组的主线不是通用搜索引擎或纯 IR，但已经明确进入“检索 + 推理 + 事实性评测”：2025 年的
RAEmoLLM 使用检索到的跨域样本做 in-context learning；2026 年又出现 RAAR、Plan Then Retrieve、
DR³-Eval、TVIR 以及深度研究轨迹错误定位。因此，本项目的 BM25/Dense/Hybrid/Rerank、证据覆盖、
拒答和可复核评测不是无人指导的旁支，最合适的定位是：**为她的垂域高风险生成与深度研究评测
补上可诊断、可复现的 retrieval layer**。但如果把研究目标写成纯索引结构或检索模型训练，匹配度会下降。

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

第一遍（问题—贡献—结论）：FinBen 将 36 个数据集、24 个金融任务组织为 IE、文本分析、QA、生成、
风险管理、预测和决策七类，并首次把交易 agent 与 RAG 纳入较完整的金融 LLM 评测。15 个模型的结果
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
作者为 Zheheng Luo、Qianqian Xie、Sophia Ananiadou；论文单位为曼彻斯特大学。作者贡献声明中谢倩倩
参与 conceptualization、写作和 supervision。

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

## 2026 论文核实：她的组是否碰检索

我按武汉大学主页给出的 Google Scholar ID `UYW7X_0AAAAJ` 定位作者记录；Scholar 动态页在当前环境
未能稳定导出 2026 列表，因此以下条目以 Scholar 检索线索为起点，再用 arXiv、ACM/ACL Anthology
和 DBLP 逐条交叉核实，避免把同名作者混入。这里不把“检索到 Scholar 入口”误写成“已完整导出主页”。

- **RAAR: Retrieval Augmented Agentic Reasoning for Cross-Domain Misinformation Detection**
  ([arXiv](https://arxiv.org/abs/2601.04853))：检索语义、情感、写作风格多视角源域证据，再由专门 agent
  形成可验证推理路径，并训练 verifier。谢倩倩为作者之一。
- **Plan Then Retrieve: Reinforcement Learning-Guided Complex Reasoning over Knowledge Graphs**
  ([ACM DOI](https://doi.org/10.1145/3774904.3792191))：WWW 2026；先规划再检索知识图谱，谢倩倩单位明确列为
  武汉大学人工智能学院/语言与信息中心。
- **DR³-Eval: Towards Realistic and Reproducible Deep Research Evaluation**
  ([arXiv](https://arxiv.org/abs/2604.14683))：谢倩倩第一作者；每题配置静态 research sandbox corpus，含
  supportive documents、distractors 和 noise，并评 Information Recall、Factual Accuracy、Citation Coverage、
  Instruction Following、Depth Quality。这与本项目“冻结语料 + 检索召回 + 引用覆盖”最直接对齐。
- **TVIR: Building Deep Research Agents Towards Text--Visual Interleaved Report Generation**
  ([arXiv](https://arxiv.org/abs/2606.02320))：显式检索图片、生成可追溯图表并做文图双路径评测。
- **Where Do Deep-Research Agents Go Wrong?**
  ([arXiv](https://arxiv.org/abs/2606.02060))：基于真实 search/tool/evidence trajectories 做 span-level
  error localization，关注未支持或冲突 claim 如何污染答案路径。
- ACL 2026 另有 MultiFinBen、ClinicalSkillQA、EmCellLLM、TaxPraBen 等 benchmark 工作，继续强化她的
  垂域评测取向；其中 MultiFinBen 已要求跨语言、多模态证据整合。

判断：她的组不仅“碰检索”，而且 2026 年把检索推进到 agentic reasoning 与 deep-research evaluation。
项目的半套 IR 工作是可被指导的补充；最强套磁切口是 DR³-Eval 的静态可验证 corpus 与 retrieval robustness，
其次是 RAAR 的多视角 evidence retrieval。不要把自己写成要在她组内独立做传统 IR leaderboard。

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
