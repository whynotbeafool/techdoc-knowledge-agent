# 整稿阶段审校：2026-09-11

## 已完成的阶段产物

- 论文结构完整：Abstract、Introduction、Related Work、Methods、Results、Discussion、Limitations、Conclusion。
- 三方法结果绑定 `frozen-30-hybrid-rrf-v1`，区分双 cohort、边际分层、反证检索与无答案题。
- 完成原 any-overlap 指标的事后字符覆盖审计；可复跑脚本与 7 个区间边界测试均已完成。
- 第一轮压缩聚焦 Introduction 与 Discussion 的重复结果复述，保留 Methods 的操作性定义和 Results 的双口径表。

## 本轮一手文献核查与更正

| 主张 | 来源位置 | 审校结果 |
|---|---|---|
| BEIR 仅提出偏差警告，没有实证处理 | [BEIR §6、Table 4](https://arxiv.org/html/2104.08663v4) | 不成立。其补标 980 对 TREC-COVID 查询—文档并重算结果；正文已明确，旧脚手架已纠正。 |
| 词汇配额证明本项目无标注偏差 | 同上，加本项目构造协议 | 不成立。pooling 与措辞偏差是不同对象；只保留降低风险的说法。 |
| DomainRAG 的 BM25 优势属于精确实体任务的独立检索结论 | [DomainRAG §4.1–4.3、Table 2](https://arxiv.org/html/2406.05654v2) | 改为 BM25 检索配置下的下游结果总体较好，明确对照 BGE-base-zh-v1.5。不把答案级表现写成独立 retriever recall 结论。 |
| TreatFact 78 篇双标及 0.73–0.94 / 0.55 | [期刊版 Appendix C.1、Table C.5，第 7 页](https://arxiv.org/pdf/2402.13758v2) | 数字可核对。沿用 overall factual-consistency agreement，不擅自称 κ，也不把差异当作分维判断普遍更优的证明。 |

本轮聚焦上述三个高影响论断，并非重新审完全部六篇论文。
FinBen、RAGAS、Self-RAG 的完整 claim-to-source 对照仍需做；引用键存在不等于每条主张都已核验。
Methods 的 BM25、MiniLM、RRF 方法文献及句向量模型卡已补齐；当前共 10 条引用。
RRF 原论文核对了名次倒数求和与常数 60；Top-20 候选深度来自本项目 config。
MiniLM 原论文与 all-MiniLM-L6-v2 模型卡分开引用，避免把基础模型压缩工作等同于具体句向量权重。
BM25 2009 综述的出版元数据可查，但出版商全文本轮返回 403；本项目的参数与分词行为依据本地实现，
不声称已对照全文逐式验证 BM25 变体。

### 方法引用来源

- [RRF 作者公开稿](https://cormack.uwaterloo.ca/cormack/cormacksigir09-rrf.pdf)：第 1 页公式与常数 60。
- [RRF 出版元数据](https://research.google/pubs/reciprocal-rank-fusion-outperforms-condorcet-and-individual-rank-learning-methods/)：作者、SIGIR 2009、758–759 页。
- [BM25 综述出版页](https://doi.org/10.1561/1500000019)：方法归属与文献元数据；全文核查仍有限制。
- [MiniLM NeurIPS 2020](https://proceedings.neurips.cc/paper/2020/hash/3f5ee243547dee91fbd053c1c4a845aa-Abstract.html)：模型压缩方法来源。
- [Sentence Transformers 模型卡](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)：具体句向量模型的说明，访问日 2026-09-11。

模型卡的默认输入截断说明不能自动视为历史 Chroma ONNX 运行的实测设置；后续应检查实际 tokenizer、
模型 artifact 和输入长度。当前没有据此添加“800 字符不会被截断”的保证。

## 可以汇报的结论

确认可答题的 Top-5 原完整命中：BM25 8/17、Dense 7/17、Hybrid 9/17。
严格字符并集覆盖后为 6/17、5/17、8/17，排序保留，但部分下降只因丢失换行。
Hybrid 的较早排名指标并非最佳；低重叠层 Dense 较好。结果支持局部取舍，不支持普遍胜者。
可审计的坐标与记录是当前最扎实的产物；可靠区分检索失败与生成失败仍是待验证目标。

## 下一阶段按依赖顺序推进

1. **正式复标**：按既定计划完成 14 题，保留隐藏首轮答案/证据与 baseline 的流程；复标尚无正式记录。
   已看过的审计案例可能影响记忆，需要如实记录暴露情况。不能由已读取 gold 的助手代填后宣称独立盲标。
2. **一致性报告**：逐个人工维度记录差异与裁决；只称 intra-annotator temporal consistency。
3. **覆盖指标规范**：预先明确空白、区间并集和等价证据处理；本轮事后敏感性不替换原指标或旧 run。
4. **引用和来源补齐**：完成其余 claim 核查、补方法引用与语料来源清单；检查引用内容与出版版本对应。
5. **复现配置**：未来新 run 明确距离/index 设置和模型 artifact；不可倒填历史运行中未保存的信息。
6. **投稿准备**：选模板后再编译、压页数与核对图表；当前尚无投稿版式验证。

本文档不意味着以上实验已获得执行结果；它区分当前稿件完成度和证据完成度。
