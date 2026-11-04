"""Compute the metrics reported in the paper from the judge scores.

- Mean judge score per model and prompting configuration, with 95% CIs from a
  patient-level bootstrap (2,000 resamples).
- Best configuration of each model: highest mean over all documented pairs.
- Per-question scores under the best configuration (Table 1).
- DR findings split by reference polarity: sensitivity-like (lesion documented as present)
  and specificity-like (documented as absent), and the per-question balanced score.
- With --answers: share of answers to documented lesions that deny them (best configuration).
- Question enrichment: paired differences against the original questions.

Usage:
    python 6_analysis/metrics.py --benchmark benchmark.jsonl --judgments results/judgments.jsonl
"""
import argparse
from pathlib import Path
import re

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent.parent
N_BOOT, SEED = 2000, 42
LESION_CATEGORY = "CAT_RETINOPATIA_DIABETICA"
ILLUMINATION = "CAT_CALIDAD_IMAGEN:4"
# Balanced score: only questions with at least this many present and absent references.
MIN_PER_CLASS = 20
# Fixed rule on the reference text (Spanish). All matches were checked manually; "mixed"
# references (an absence plus a connector that may introduce a finding) need manual review.
NEGATIVE = re.compile(r"^\s*(no\b|sin\b|ausencia|los vasos no|vasos:?\s+sin)|sin particularidades|no se describen",
                      re.IGNORECASE)
MIXED = re.compile(r"\b(pero|aunque|sin embargo|excepto|salvo)\b|\bs[ií]\s+se\b", re.IGNORECASE)
# Fixed rule on the model answer (Spanish): it denies the asked lesion unless it starts with "Sí".
# A random sample of 30 matches was checked manually.
DENIAL = re.compile(r"^\W*no\b|\bno se (observa|identifica|detecta|aprecia|evidencia|visualiza|ve|puede)"
                    r"|\bno (hay|presenta|existen|muestra)\b|\bsin (signos|evidencia)|\bausencia de", re.IGNORECASE)
AFFIRMATION = re.compile(r"^\W*s[ií]\b", re.IGNORECASE)
CONFIG = ["strategy", "framing"]


def polarity(text):
    """Present (including uncertain findings such as "compatible con"), absent or mixed."""
    if NEGATIVE.search(text):
        return "mixed" if MIXED.search(text) else "negative"
    return "positive"


def denies(answer):
    return bool(DENIAL.search(answer)) and not AFFIRMATION.match(answer)


def read_jsonl(path):
    return pd.read_json(path, lines=True, dtype={"patient_id": str, "image_id": str})


class Bootstrap:
    """Patient-level bootstrap: the same resamples for every group, so CIs are comparable."""

    def __init__(self, patients):
        self.patients = np.sort(pd.unique(patients))
        n = len(self.patients)
        self.weights = np.random.default_rng(SEED).multinomial(n, np.full(n, 1 / n), size=N_BOOT)

    def means(self, df, keys):
        """Mean score per group and its replicates (N_BOOT x groups)."""
        by_patient = df.groupby(["patient_id", *keys])["score"].agg(["sum", "count"]).unstack(keys, fill_value=0)
        sums = by_patient["sum"].reindex(self.patients, fill_value=0)
        counts = by_patient["count"].reindex(self.patients, fill_value=0)
        boot = pd.DataFrame((self.weights @ sums.to_numpy()) / (self.weights @ counts.to_numpy()), columns=sums.columns)
        return sums.sum() / counts.sum(), boot


def ci(point, boot):
    return pd.DataFrame({"mean": point, "lo": boot.quantile(0.025), "hi": boot.quantile(0.975)})


def balanced(bootstrap, lesions, keys, questions):
    """Mean of sensitivity- and specificity-like within each question, then over questions."""
    df = lesions[lesions["question_id"].isin(questions)]
    point, boot = bootstrap.means(df, [*keys, "question_id", "polarity"])

    def combine(table):
        both = (table.xs("positive", axis=1, level="polarity") + table.xs("negative", axis=1, level="polarity")) / 2
        return both.T.groupby(level=keys).mean().T

    return combine(point.to_frame().T).iloc[0], combine(boot)


def fmt(table):
    return table.apply(lambda r: f"{r['mean']:.2f} [{r['lo']:.2f}, {r['hi']:.2f}]", axis=1)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--benchmark", type=Path, required=True)
    parser.add_argument("--judgments", type=Path, required=True, help="judge.py output for the 15 configurations.")
    parser.add_argument("--enriched-judgments", type=Path, help="judge.py output for the enriched questions.")
    parser.add_argument("--answers", type=Path, help="run_vqa.py output for the 15 configurations.")
    parser.add_argument("--questions", type=Path, default=ROOT / "questions/questions.yaml")
    return parser.parse_args()


def main():
    args = parse_args()
    labels = {q: spec["label_en"] for q, spec in
              yaml.safe_load(args.questions.read_text(encoding="utf-8"))["questions"].items()}
    benchmark = read_jsonl(args.benchmark)
    judgments = read_jsonl(args.judgments)
    bootstrap = Bootstrap(judgments["patient_id"])
    pd.set_option("display.width", 160)

    point, boot = bootstrap.means(judgments, ["model", *CONFIG])
    configs = ci(point, boot)
    print("Mean score per model and configuration (95% CI):")
    print(fmt(configs).unstack("framing").to_string(), "\n")

    print("Strategy and framing effects (means over the other factor):")
    by_strategy = judgments.groupby(["model", "strategy"])["score"].mean().unstack()
    by_framing = judgments.groupby(["model", "framing"])["score"].mean().unstack()
    print(by_strategy.round(2).to_string(), "\n")
    print(by_framing.round(2).to_string())
    print("Largest difference between framings within a model:",
          f"{(by_framing.max(axis=1) - by_framing.min(axis=1)).max():.2f}", "\n")
    illumination = judgments["question_id"] == ILLUMINATION
    print(f"Strategies on the illumination question ({labels[ILLUMINATION]}) and without it:")
    print(pd.DataFrame({
        "illumination": judgments[illumination].groupby(["model", "strategy"])["score"].mean(),
        "without illumination": judgments[~illumination].groupby(["model", "strategy"])["score"].mean(),
    }).round(2).to_string(), "\n")

    best = configs["mean"].groupby(level="model").idxmax()
    best = pd.DataFrame(list(best), columns=["model", *CONFIG])
    best_judgments = judgments.merge(best, on=["model", *CONFIG])
    print("Best configuration of each model:")
    print(best.to_string(index=False), "\n")
    table = best_judgments.pivot_table(index="question_id", columns="model", values="score", aggfunc="mean")
    table.insert(0, "n", benchmark.groupby("question_id").size())
    table = table.reindex([q for q in labels if q in table.index]).rename(index=labels)
    table.loc["All"] = [len(benchmark), *best_judgments.groupby("model")["score"].mean().loc[table.columns[1:]]]
    print("Table 1: mean score per question under the best configuration:")
    print(table.to_string(formatters={"n": "{:.0f}".format}, float_format="{:.2f}".format), "\n")

    refs = benchmark[benchmark["question_id"].str.startswith(LESION_CATEGORY)].copy()
    refs["polarity"] = refs["reference"].map(polarity)
    counts = refs.groupby(["question_id", "polarity"]).size().unstack(fill_value=0)
    counts = counts.reindex([q for q in labels if q in counts.index])
    print("Lesion references by polarity (check every 'mixed' one manually):")
    print(counts.rename(index=labels).to_string(), "\n")
    by_class = counts.reindex(columns=["positive", "negative"], fill_value=0)
    eligible = [q for q in by_class.index if by_class.loc[q].min() >= MIN_PER_CLASS]
    print("Questions in the balanced score:", ", ".join(labels[q] for q in eligible), "\n")

    keys = ["image_id", "question_id", "polarity"]
    lesions = best_judgments.merge(refs[keys], on=["image_id", "question_id"])
    sens = ci(*bootstrap.means(lesions, ["model", "polarity"]))
    bal = ci(*balanced(bootstrap, lesions, ["model"], eligible))
    print("DR findings, best configuration (Fig. 2b):")
    print(pd.DataFrame({"sensitivity-like": fmt(sens.xs("positive", level="polarity")),
                        "specificity-like": fmt(sens.xs("negative", level="polarity")),
                        "balanced": fmt(bal)}).to_string(), "\n")

    if args.answers:
        answers = read_jsonl(args.answers).merge(best, on=["model", *CONFIG])
        present = answers.merge(refs.loc[refs["polarity"] == "positive", ["image_id", "question_id"]],
                                on=["image_id", "question_id"])
        print("Answers to documented lesions that deny them, best configuration:")
        print(present["response"].map(denies).groupby(present["model"]).mean().map("{:.0%}".format).to_string(), "\n")

    if args.enriched_judgments:
        enriched = read_jsonl(args.enriched_judgments)
        control = judgments[(judgments["strategy"] == "direct_answering") & (judgments["framing"] == "direct_command")]
        overall = {}
        for name, data in [("original", control), ("enriched", enriched)]:
            overall[name] = bootstrap.means(data, ["model"])
        print("Question enrichment, all questions (mean score):")
        print(pd.DataFrame({"original": overall["original"][0], "enriched": overall["enriched"][0],
                            "difference": fmt(ci(overall["enriched"][0] - overall["original"][0],
                                                 overall["enriched"][1] - overall["original"][1]))}).round(2)
              .to_string(), "\n")
        rows = {}
        for name, data in [("original", control), ("enriched", enriched)]:
            lesions = data.merge(refs[keys], on=["image_id", "question_id"])
            sens = bootstrap.means(lesions, ["model", "polarity"])[0]
            rows[name] = (sens.xs("positive", level="polarity"), sens.xs("negative", level="polarity"),
                          *balanced(bootstrap, lesions, ["model"], eligible))
        print("Question enrichment, DR findings (paired, same patients in every resample):")
        print(pd.DataFrame({
            "sens. original": rows["original"][0], "sens. enriched": rows["enriched"][0],
            "spec. original": rows["original"][1], "spec. enriched": rows["enriched"][1],
            "balanced original": rows["original"][2], "balanced enriched": rows["enriched"][2],
        }).round(2).to_string())
        print(fmt(ci(rows["enriched"][2] - rows["original"][2], rows["enriched"][3] - rows["original"][3]))
              .rename("balanced difference").to_string())


if __name__ == "__main__":
    main()
