from src.data_utils import (
    load_shuffled_test_split,
    load_summaries_from_logs,
    get_gold_xsum_data,
    load_xsum_dict,
)
from sumtool.storage import get_summaries
from src.evaluation.factuality import evaluate_factuality

TEST_SIZE = 100


def load_data(results_path: str):
    if "results" in results_path:
        # load fbs results
        sums_by_id, sum_ents_by_id = load_summaries_from_logs(results_path)
    else:
        # load from sumtool
        sums_by_id = {
            sum_id: x["summary"]
            for sum_id, x in get_summaries("xsum", results_path).items()
        }
        sum_ents_by_id = {}
    gold_sums, gold_metadata = get_gold_xsum_data()
    xsum_test = load_xsum_dict("test")
    test_set_ids = set(
        load_shuffled_test_split(xsum_test, "bart-test-extrinsic", 100).keys()
    )

    filtered_sums_by_id = {
        sum_id: x for sum_id, x in sums_by_id.items() if sum_id in test_set_ids
    }
    filtered_ents_by_id = {
        sum_id: x for sum_id, x in sum_ents_by_id.items() if sum_id in test_set_ids
    }
    return (
        filtered_sums_by_id,
        filtered_ents_by_id,
        gold_sums,
        gold_metadata,
        xsum_test,
    )


def test_evaluate_factuality_oracle():
    (
        sums_by_id,
        sum_ents_by_id,
        gold_sums,
        gold_metadata,
        xsum_test,
    ) = load_data("results/fbs-logs/bart-test-extrinsic-oracle.json")
    agg_metrics, summaries = evaluate_factuality(
        sums_by_id,
        sum_ents_by_id,
        gold_sums,
        gold_metadata,
        xsum_test,
        should_annotate=False,
        entity_match_type="strict_intrinsic",
        print_first_n=0,
        is_fbs=True,
        is_oracle=True,
        count_skips=True,
    )
    # These metrics might change if the dataset changes
    assert agg_metrics["summaries"]["total"] == 100
    assert agg_metrics["summaries"]["factual"] == 0.65
    assert agg_metrics["summaries"]["non_factual"] == 0.12
    assert agg_metrics["summaries"]["skipped"] == 0.23
    assert agg_metrics["summaries"]["failed"] == 7
    assert agg_metrics["entities"]["Unknown"] == 0
    assert agg_metrics["entities"]["Factual Hallucination"] == 88
    assert agg_metrics["entities"]["Intrinsic Hallucination"] == 14
    assert agg_metrics["entities"]["Non-hallucinated"] == 154
    assert agg_metrics["entities"]["total"] == 88 + 14 + 154

    # CRUCIAL: Oracle should have 0 non factual hallucinations because they're skipped
    assert agg_metrics["summaries"]["non_factual_extrinsic"] == 0
    assert agg_metrics["entities"]["Non-factual Hallucination"] == 0

    # This also means that extrinsic factuality ratio should always be 1.
    assert agg_metrics["entities"]["extrinsic_factuality_ratio"]["mean"] == 1
    assert agg_metrics["entities"]["extrinsic_factuality_ratio"]["stdev"] == 0

    # All non factual errors stem from intrinsic hallucinations
    assert (
        agg_metrics["summaries"]["non_factual"]
        == agg_metrics["summaries"]["non_factual_intrinsic"]
    )
    # Should sum to 1
    assert (
        sum(
            [
                agg_metrics["summaries"]["factual"],
                agg_metrics["summaries"]["non_factual"],
                agg_metrics["summaries"]["skipped"],
            ]
        )
        == 1
    )


def test_evaluate_factuality_oracle_no_skips():
    (
        sums_by_id,
        sum_ents_by_id,
        gold_sums,
        gold_metadata,
        xsum_test,
    ) = load_data("results/fbs-logs/bart-test-extrinsic-oracle.json")
    agg_metrics, summaries = evaluate_factuality(
        sums_by_id,
        sum_ents_by_id,
        gold_sums,
        gold_metadata,
        xsum_test,
        should_annotate=False,
        entity_match_type="strict_intrinsic",
        print_first_n=0,
        is_fbs=True,
        is_oracle=True,
        count_skips=False,
    )
    # These metrics might change if the dataset changes
    assert agg_metrics["summaries"]["total"] == 100
    assert agg_metrics["summaries"]["factual"] == 0.65
    assert agg_metrics["summaries"]["non_factual"] == 0.35
    assert agg_metrics["summaries"]["failed"] == 7
    assert agg_metrics["entities"]["Unknown"] == 0
    assert agg_metrics["entities"]["Factual Hallucination"] == 98
    assert agg_metrics["entities"]["Intrinsic Hallucination"] == 16
    assert agg_metrics["entities"]["Non-factual Hallucination"] == 23
    assert agg_metrics["entities"]["Non-hallucinated"] == 177
    assert agg_metrics["entities"]["total"] == 98 + 16 + 23 + 177

    assert agg_metrics["entities"]["extrinsic_factuality_ratio"]["mean"] == 0.9661764705882353


def test_evaluate_factuality_classifier():
    (
        sums_by_id,
        sum_ents_by_id,
        gold_sums,
        gold_metadata,
        xsum_test,
    ) = load_data("results/fbs-logs/bart-test-extrinsic-classifier-knnv1.json")
    agg_metrics, summaries = evaluate_factuality(
        sums_by_id,
        sum_ents_by_id,
        gold_sums,
        gold_metadata,
        xsum_test,
        should_annotate=False,
        entity_match_type="strict_intrinsic",
        print_first_n=0,
        is_fbs=True,
        is_oracle=False,
        count_skips=True
    )
    assert agg_metrics["summaries"]["total"] == 100
    assert agg_metrics["summaries"]["factual"] == 0.48
    assert agg_metrics["summaries"]["non_factual"] == 0.27
    assert agg_metrics["summaries"]["non_factual_extrinsic"] == 0.2
    assert agg_metrics["summaries"]["non_factual_intrinsic"] == 0.1
    assert agg_metrics["summaries"]["skipped"] == 0.25
    assert agg_metrics["summaries"]["failed"] == 14
    assert agg_metrics["summaries"]["unknown"] == 0
    assert agg_metrics["entities"]["Unknown"] == 0
    assert agg_metrics["entities"]["Non-factual Hallucination"] == 23
    assert agg_metrics["entities"]["Factual Hallucination"] == 63
    assert agg_metrics["entities"]["Intrinsic Hallucination"] == 11
    assert agg_metrics["entities"]["Non-hallucinated"] == 145
    assert agg_metrics["entities"]["total"] == 23 + 63 + 11 + 145

    assert agg_metrics["entities"]["extrinsic_factuality_ratio"]["mean"] == 0.9450980392156864

    # Should sum to 1
    assert (
        sum(
            [
                agg_metrics["summaries"]["factual"],
                agg_metrics["summaries"]["non_factual"],
                agg_metrics["summaries"]["skipped"],
            ]
        )
        == 1
    )


def test_evaluate_factuality_classifier_no_skips():
    (
        sums_by_id,
        sum_ents_by_id,
        gold_sums,
        gold_metadata,
        xsum_test,
    ) = load_data("results/fbs-logs/bart-test-extrinsic-classifier-knnv1.json")
    agg_metrics, summaries = evaluate_factuality(
        sums_by_id,
        sum_ents_by_id,
        gold_sums,
        gold_metadata,
        xsum_test,
        should_annotate=False,
        entity_match_type="strict_intrinsic",
        print_first_n=0,
        is_fbs=True,
        is_oracle=False,
        count_skips=False,
    )
    # These metrics might change if the dataset changes
    assert agg_metrics["summaries"]["total"] == 100
    assert agg_metrics["summaries"]["factual"] == 0.50
    assert agg_metrics["summaries"]["non_factual"] == 0.50
    assert agg_metrics["summaries"]["non_factual_extrinsic"] == 0.29
    assert agg_metrics["summaries"]["non_factual_intrinsic"] == 0.13
    assert agg_metrics["summaries"]["skipped"] == 0
    assert agg_metrics["summaries"]["failed"] == 14
    assert agg_metrics["summaries"]["unknown"] == 0
    assert agg_metrics["entities"]["Unknown"] == 0
    assert agg_metrics["entities"]["Factual Hallucination"] == 76
    assert agg_metrics["entities"]["Intrinsic Hallucination"] == 14
    assert agg_metrics["entities"]["Non-factual Hallucination"] == 37
    assert agg_metrics["entities"]["Non-hallucinated"] == 164
    assert agg_metrics["entities"]["total"] == 76 + 14 + 37 + 164

    assert agg_metrics["entities"]["extrinsic_factuality_ratio"]["mean"] == 0.8988700564971751


def test_evaluate_factuality_baseline():
    (
        sums_by_id,
        sum_ents_by_id,
        gold_sums,
        gold_metadata,
        xsum_test,
    ) = load_data("facebook-bart-large-xsum")
    agg_metrics, summaries = evaluate_factuality(
        sums_by_id,
        sum_ents_by_id,
        gold_sums,
        gold_metadata,
        xsum_test,
        should_annotate=False,
        entity_match_type="strict_intrinsic",
        print_first_n=0,
        is_fbs=False,
        is_oracle=False,
    )
    assert agg_metrics["summaries"]["total"] == 100
    assert agg_metrics["summaries"]["factual"] == 0.41
    assert agg_metrics["summaries"]["non_factual"] == 0.59
    assert agg_metrics["summaries"]["non_factual_extrinsic"] == 0.52
    assert agg_metrics["summaries"]["non_factual_intrinsic"] == 0.12
    assert agg_metrics["summaries"]["skipped"] == 0
    assert agg_metrics["summaries"]["failed"] == 0
    assert agg_metrics["summaries"]["unknown"] == 0
    assert agg_metrics["entities"]["Non-factual Hallucination"] == 74
    assert agg_metrics["entities"]["Unknown"] == 0
    assert agg_metrics["entities"]["Factual Hallucination"] == 94
    assert agg_metrics["entities"]["Intrinsic Hallucination"] == 13
    assert agg_metrics["entities"]["Non-hallucinated"] == 188
    assert agg_metrics["entities"]["total"] == 74 + 94 + 13 + 188

    assert agg_metrics["entities"]["extrinsic_factuality_ratio"]["mean"] == 0.8128571428571428

    # Should sum to 1
    assert (
        sum(
            [
                agg_metrics["summaries"]["factual"],
                agg_metrics["summaries"]["non_factual"],
                agg_metrics["summaries"]["skipped"],
            ]
        )
        == 1
    )


def test_evaluate_factuality_gold():
    (
        sums_by_id,
        sum_ents_by_id,
        gold_sums,
        gold_metadata,
        xsum_test,
    ) = load_data("gold")
    agg_metrics, summaries = evaluate_factuality(
        sums_by_id,
        sum_ents_by_id,
        gold_sums,
        gold_metadata,
        xsum_test,
        should_annotate=False,
        entity_match_type="strict_intrinsic",
        print_first_n=0,
        is_fbs=False,
        is_oracle=False,
    )
    assert agg_metrics["summaries"]["total"] == 100
    assert agg_metrics["summaries"]["factual"] == 1
    assert agg_metrics["summaries"]["non_factual"] == 0
    assert agg_metrics["summaries"]["non_factual_extrinsic"] == 0
    assert agg_metrics["summaries"]["non_factual_intrinsic"] == 0
    assert agg_metrics["summaries"]["skipped"] == 0
    assert agg_metrics["summaries"]["failed"] == 0
    assert agg_metrics["summaries"]["unknown"] == 0
    assert agg_metrics["entities"]["Non-factual Hallucination"] == 0
    assert agg_metrics["entities"]["Unknown"] == 0
    assert agg_metrics["entities"]["Factual Hallucination"] == 193
    assert agg_metrics["entities"]["Intrinsic Hallucination"] == 0
    assert agg_metrics["entities"]["Non-hallucinated"] == 173
    assert agg_metrics["entities"]["total"] == 193 + 173

    assert agg_metrics["entities"]["extrinsic_factuality_ratio"]["mean"] == 1
    assert agg_metrics["entities"]["extrinsic_factuality_ratio"]["stdev"] == 0

    # Should sum to 1
    assert (
        sum(
            [
                agg_metrics["summaries"]["factual"],
                agg_metrics["summaries"]["non_factual"],
                agg_metrics["summaries"]["skipped"],
            ]
        )
        == 1
    )
