"""Measure how often model answers reproduce example wording from the prompts.

Two checks reported in the paper, computed on the raw answers (run_vqa.py output):
- Few-shot prompting: share of answers to the illumination question that use the word of the
  illumination example ("subexpuesta", underexposed), per model and strategy.
- Enriched questions: share of answers to each question that are exactly one of the example
  answers of that enriched question (Ejemplo A is the positive example).

Usage:
    python 6_analysis/answer_copying.py --answers vqa_answers.jsonl \
        --enriched-answers vqa_answers_enriched.jsonl
"""
import argparse
from pathlib import Path
import re

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent.parent
ILLUMINATION = "CAT_CALIDAD_IMAGEN:4"
EXAMPLE = re.compile(r'Ejemplo ([A-Z])\. .*?Respuesta: "([^"]+)"')


def normalize(text):
    return " ".join(text.split()).casefold()


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--answers", type=Path, help="Answers to the original questions (15 configurations).")
    parser.add_argument("--enriched-answers", type=Path, help="Answers to the enriched questions.")
    parser.add_argument("--enriched-questions", type=Path, default=ROOT / "questions/enriched_questions.yaml")
    args = parser.parse_args()

    if args.answers:
        answers = pd.read_json(args.answers, lines=True)
        illumination = answers[answers["question_id"] == ILLUMINATION].copy()
        illumination["underexposed"] = illumination["response"].str.contains("subexpuest", case=False)
        print("Illumination answers that say 'subexpuesta' (underexposed):")
        print(illumination.groupby(["model", "strategy"])["underexposed"].agg(["sum", "count", "mean"])
              .round(2).to_string(), "\n")

    if args.enriched_answers:
        enriched = yaml.safe_load(args.enriched_questions.read_text(encoding="utf-8"))["preguntas"]
        examples = {qid: {normalize(text): letter for letter, text in EXAMPLE.findall(entry["prompt_enriquecido"])}
                    for qid, entry in enriched.items()}
        answers = pd.read_json(args.enriched_answers, lines=True)
        answers["example"] = [examples[q].get(normalize(r)) for q, r in zip(answers["question_id"], answers["response"])]
        table = answers.groupby(["model", "question_id"]).agg(
            n=("response", "size"),
            positive_example=("example", lambda s: (s == "A").mean()),
            any_example=("example", lambda s: s.notna().mean()))
        print("Enriched questions: share of answers identical to an example answer (A = positive example):")
        print(table.round(2).to_string())


if __name__ == "__main__":
    main()
