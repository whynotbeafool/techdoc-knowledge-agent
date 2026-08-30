# frozen-30-hybrid-rrf-v1 analysis

## Controlled setup

- The QA hash, active-revision hash, 800-character chunks, BM25 settings, and
  Dense model match `frozen-30-v1`.
- The reproduced BM25 and Dense rows, including rankings and metrics, match the
  earlier frozen run.
- Hybrid uses equal-weight Reciprocal Rank Fusion with component candidate depth
  20 and rank constant 60. These parameters were fixed before viewing the run.
- All 30 Hybrid rows retain the fused score and component ranks for auditability.

## Confirmed answerable results

| Method | R@1 | R@3 | R@5 | MRR@5 | CompleteHit@5 |
|---|---:|---:|---:|---:|---:|
| BM25 | 0.4118 | 0.6471 | 0.6471 | 0.6667 | 0.4706 |
| Dense | 0.3529 | 0.5294 | 0.5588 | 0.5706 | 0.4118 |
| Hybrid-RRF | 0.4118 | 0.5000 | 0.6471 | 0.6147 | 0.5294 |

Hybrid does not improve macro Evidence Recall@5 over BM25. It raises complete
Top-5 evidence coverage by one question, but lowers Recall@3 and MRR@5.

## Pairwise diagnosis

- `q015`: Dense contributes a missing PEP 8 chunk, so Hybrid changes Top-5
  Evidence Recall from 0.5 to 1.0 and makes the evidence set complete.
- `q013`: a BM25 evidence-bearing chunk ranked third is displaced from Hybrid
  Top-5 by chunks ranked well in both components, reducing Evidence Recall from
  0.5 to 0.0.
- Other changes mainly reorder already-retrieved evidence. For example, Hybrid
  improves q009 and q012 first-relevant rank, but worsens q008, q010, and q011.

The net R@5 change is therefore zero: q015's gain is offset by q013's loss.

## Conclusions allowed

- Equal-weight RRF is implemented reproducibly and can recover complementary
  Dense evidence in individual cases.
- On this frozen dataset it trades early ranking quality for one additional
  complete Top-5 evidence set.
- A single aggregate metric would hide this trade-off.

## Conclusions not allowed

- Do not claim Hybrid is generally better than BM25 or Dense.
- Do not tune weights, candidate depth, or the rank constant on these 30 questions
  and report the same data as an unbiased comparison.
- Do not infer production latency or scalability from this offline run.
