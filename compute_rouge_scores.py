from src.data_utils import get_gold_xsum_data, load_summaries_from_logs, load_xsum_dict
from sumtool.storage import get_summaries
from src.metrics import rouge
from tqdm import tqdm
import numpy as np


if __name__ == "__main__":
    gold_sums, gold_metadata = get_gold_xsum_data()

    MODEL_RESULTS = {
        "BartGEF": load_summaries_from_logs(
            "results/fbs-logs/bart-full-classifier-knnv1.json", max_iterations=5
        ),
        # "pegasus_gef": load_summaries_from_logs(
        #     "results/fbs-logs/bart-full-classifier-knnv1.json", max_iterations=5
        # ),
    }

    sumtool_models = [
        ("facebook-bart-large-xsum", "BartBaseline"),
        ("meng-3000", "MengRL"),  # Hallucinated, but factual! Paper
        ("pinocchio", "Pinocchio"),  # King et. al paper
        ("chen-corrector", "Corrector"),  # Chen. et al replication project
        ("google-pegasus-xsum", "PegasusBaseline"),
    ]
    for (sumtool_name, model_label) in sumtool_models:
        dataset = get_summaries("xsum", sumtool_name)
        MODEL_RESULTS[model_label] = (
            {sum_id: x["summary"] for sum_id, x in dataset.items()},
            {},
        )

    rouge_scores_by_model = {}

    for model_label, (sums_by_id, sum_ents_by_id) in MODEL_RESULTS.items():
        rouge1 = []
        rouge2 = []
        rougeL = []
        for sum_id, summary in tqdm(list(sums_by_id.items())):
            reference = gold_sums[sum_id]
            scores = rouge([summary], [reference])
            rouge1.append(scores["rouge1"]["f1"])
            rouge2.append(scores["rouge2"]["f1"])
            rougeL.append(scores["rougeL"]["f1"])
        rouge_scores_by_model[model_label] = {
            "RougeOne": np.mean(rouge1),
            "RougeTwo": np.mean(rouge2),
            "RougeL": np.mean(rougeL),
        }

    with open("results/latex/rouge_scores.tex", "w") as f:
        for model_label, results in rouge_scores_by_model.items():
            for metric_label, metric in results.items():
                str = (
                    f"\\newcommand{{\\{model_label}{metric_label}}}{{{metric * 100:.2f}}}"
                    + "\n"
                )
                f.write(str.replace("%", "\\%"))