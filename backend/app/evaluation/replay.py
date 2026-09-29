"""Offline paired policy replay and group bootstrap; no model calls or judgments."""

import math
import random

from app.evaluation.selective import select_working_point, selective_summary, validate_group_split
from app.rag.gating import ContextChunk, gate, runtime_features

POLICY_REFUSAL = "I cannot provide an evidence-supported answer from the retrieved context."

TARGETS = ("answer", "correct_premise", "refuse")
LEXICAL_GRID = (0, 0.25, 0.5, 0.75, 1)


def score_grid(scores, *, split):
    if split != "dev":
        raise ValueError("Score grid is development-only")
    values = []
    for value in scores:
        if value is None:
            continue
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError("Score grid requires finite scores")
        values.append(float(value))
    if not values:
        return [0.0]  # Empty retrieval: all B/C policies reject.
    unique = sorted(set(values))
    lower, upper = math.nextafter(unique[0], -math.inf), math.nextafter(unique[-1], math.inf)
    if not math.isfinite(lower) or not math.isfinite(upper):
        raise ValueError("No finite outer score-grid boundary")
    return [lower, *unique, upper]


def stratified_summary(rows):
    if any(r["expected_behavior"] not in TARGETS for r in rows):
        raise ValueError("Unknown response target")
    return {
        "overall": selective_summary(rows),
        "by_target": {
            target: selective_summary([r for r in rows if r["expected_behavior"] == target])
            for target in TARGETS
        },
    }


def replay_policy(rows, *, strategy, score_threshold=0.0, lexical_threshold=0.0):
    scored, events = [], []
    for row in rows:
        chunks = [ContextChunk(**chunk) for chunk in row["chunks"]]
        decision = gate(
            row["question"],
            chunks,
            strategy=strategy,
            score_threshold=score_threshold,
            lexical_threshold=lexical_threshold,
        )
        result = dict(
            row["judgment"],
            question_id=row["question_id"],
            expected_behavior=row["expected_behavior"],
            group_id=row["group_id"],
        )
        if not decision["allow_generation"]:
            result.update(
                execution_status="ok", behavior="refusal", correct=None, complete=None, supported=None
            )
        scored.append(result)
        events.append(
            {
                "question_id": row["question_id"],
                **decision,
                "event": "cached_baseline" if decision["allow_generation"] else "policy_refusal",
                "policy_response": None if decision["allow_generation"] else POLICY_REFUSAL,
                "score_threshold": score_threshold,
                "lexical_threshold": lexical_threshold,
            }
        )
    summary = stratified_summary(scored)
    return {
        "strategy": strategy,
        "score_threshold": score_threshold,
        "lexical_threshold": lexical_threshold,
        "generation_call_n": sum(e["allow_generation"] for e in events),
        "summary": summary["overall"],
        "by_target": summary["by_target"],
        "events": events,
    }, scored


def replay_development(rows):
    validate_group_split(rows, enforce_assignment=True)
    if not rows or any(r["split"] != "dev" for r in rows):
        raise ValueError("Development replay requires nonempty dev-only rows")
    # Validate judgments before gates could hide invalid or unjudged baseline responses.
    baseline, _ = replay_policy(rows, strategy="A")
    grid = score_grid(
        [
            runtime_features(r["question"], [ContextChunk(**c) for c in r["chunks"]])["top_score"]
            for r in rows
        ],
        split="dev",
    )
    candidates = {"B": [], "C": []}
    for strategy in candidates:
        for threshold in grid:
            for lexical in (0,) if strategy == "B" else LEXICAL_GRID:
                candidate, _ = replay_policy(
                    rows, strategy=strategy, score_threshold=threshold, lexical_threshold=lexical
                )
                candidates[strategy].append(candidate)
    incomplete = any(
        r["judgment"].get("behavior") is None and r["judgment"]["execution_status"] == "ok" for r in rows
    )
    incomplete |= any(
        r["judgment"].get(k) is None for r in rows for k in ("corpus_supported", "context_sufficient")
    )
    incomplete |= any(
        r["judgment"].get(k) is None
        for r in rows
        if r["judgment"].get("behavior") in {"answer", "partial", "correction"}
        for k in ("correct", "complete", "supported")
    )
    selections = {
        strategy: {
            str(target): (
                {"status": "incomplete_annotations", "selected": None}
                if incomplete
                else select_working_point(items, split="dev", min_coverage=target)
            )
            for target in (0.5, 0.25, 0.75)
        }
        for strategy, items in candidates.items()
    }
    return {
        "status": "offline_development_replay",
        "remote_calls": 0,
        "labels_complete": not incomplete,
        "score_grid": grid,
        "lexical_grid": list(LEXICAL_GRID),
        "baseline": baseline,
        "candidates": candidates,
        "selections": selections,
        "scope": "Supplied cached outputs and judgments; not independent validation or live cost savings",
    }


def grouped_bootstrap(rows_by_strategy, *, resamples=2000, seed=20260928):
    """Resample group sufficient counts; normal input uniqueness stays mandatory.

    Same draws across strategies; undefined risk is retained and disclosed.
    Intervals are descriptive percentile intervals, never proof of adequate power.
    """
    if type(resamples) is not int or resamples < 1 or type(seed) is not int:
        raise ValueError("Positive resample count and integer seed required")
    if not rows_by_strategy:
        raise ValueError("At least one strategy required")
    reference = None
    counts = {}
    for strategy, rows in rows_by_strategy.items():
        selective_summary(rows)  # Includes original question-ID uniqueness validation.
        mapping = {r["question_id"]: r["group_id"] for r in rows}
        if any(not isinstance(g, str) or not g for g in mapping.values()):
            raise ValueError("Nonempty group IDs required")
        if reference is not None and mapping != reference:
            raise ValueError("Paired strategies must have identical question/group membership")
        reference = mapping
        counts[strategy] = {
            g: selective_summary([r for r in rows if r["group_id"] == g])["metrics"]
            for g in sorted(set(mapping.values()))
        }
    groups = sorted(set(reference.values()))
    if len(groups) < 2:
        return {
            "status": "insufficient_groups",
            "group_n": len(groups),
            "resamples": 0,
            "seed": seed,
            "intervals": None,
        }
    metrics = list(next(iter(next(iter(counts.values())).values())))
    draws = {s: {m: [] for m in metrics} for s in counts}
    rng = random.Random(seed)
    for _ in range(resamples):
        sample = rng.choices(groups, k=len(groups))
        for strategy, group_counts in counts.items():
            for metric in metrics:
                parts = [group_counts[g][metric] for g in sample]
                missing = any(p["missing_label_rows"] for p in parts)
                denominator = None if missing else sum(p["denominator"] for p in parts)
                value = sum(p["numerator"] for p in parts) / denominator if denominator else None
                draws[strategy][metric].append(value)

    def interval(values, *, strategies, metric):
        valid = sorted(v for v in values if v is not None)
        fraction = 1 - len(valid) / len(values)
        # Missing original labels invalidate an interval even if some draws omit their group.
        complete = all(
            not cell[m]["missing_label_rows"]
            for strategy in strategies
            for cell in counts[strategy].values()
            for m in (metric,)
        )

        def quantile(p):
            index = (len(valid) - 1) * p
            low, high = math.floor(index), math.ceil(index)
            return valid[low] + (valid[high] - valid[low]) * (index - low)

        return {
            "undefined_fraction": fraction,
            "defined_n": len(valid),
            "interval_95": [quantile(0.025), quantile(0.975)] if complete and fraction < 0.5 else None,
        }

    first = next(iter(draws))
    return {
        "status": "descriptive_group_bootstrap",
        "group_n": len(groups),
        "resamples": resamples,
        "seed": seed,
        "reference_strategy": first,
        "intervals": {
            s: {m: interval(v, strategies=(s,), metric=m) for m, v in rates.items()}
            for s, rates in draws.items()
        },
        "paired_differences": {
            s: {
                m: interval(
                    [
                        a - b if a is not None and b is not None else None
                        for a, b in zip(rates[m], draws[first][m])
                    ],
                    strategies=(s, first),
                    metric=m,
                )
                for m in metrics
            }
            for s, rates in draws.items()
            if s != first
        },
    }
