import pytest
from app.evaluation.grouping import build_groups


def question(qid, facts, *, parents=None, exposed=False, prior=None):
    return dict(question_id=qid, necessary_fact_ids=facts, parent_question_ids=parents or [],
                previously_exposed=exposed, prior_group_id=prior)


def test_transitive_fact_bridge_propagates_exposure():
    rows = [question("a", ["x"], exposed=True), question("b", ["x", "y"]),
            question("c", ["y"]), question("d", ["z"], parents=["c"])]
    result = build_groups(rows)
    assert len({row["group_id"] for row in result}) == 1
    assert all(row["split"] == "dev" and row["group_previously_exposed"] for row in result)
    assert result == build_groups(list(reversed(rows)))


def test_legacy_cannot_be_laundered_with_false_exposure():
    rows = [question("q001", ["x"]), question("q030", ["y"]),
            question("new", ["z"], parents=["q030"])]
    result = build_groups(rows)
    assert all(row["group_id"] == "legacy-exposed-30" and row["split"] == "dev" for row in result)


def test_prior_group_and_fact_ids_have_separate_namespaces():
    rows = [question("a", ["x"], prior="p", exposed=True),
            question("b", ["y"], prior="p"), question("c", ["p"])]
    result = build_groups(rows)
    assert result[0]["group_id"] == result[1]["group_id"]
    assert result[2]["group_id"] != result[0]["group_id"]
    assert result[2]["group_previously_exposed"] is False


@pytest.mark.parametrize("rows", [
    [question("a", ["x"], parents=["missing"])],
    [question("a", ["x"], parents=["a"])],
    [question("a", [])],
    [question("a", ["x"], exposed=None)],
    [question("a", ["x"]), question("a", ["y"])],
    [question("a", ["x", "x"])],
])
def test_rejects_incomplete_or_ambiguous_provenance(rows):
    with pytest.raises(ValueError):
        build_groups(rows)
