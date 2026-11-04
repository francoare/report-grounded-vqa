"""Ask local MLLMs (Ollama) the benchmark questions about each fundus photograph.

Each request contains one system prompt (a prompting configuration), the question and the
image; the model never sees the report or the reference. Results go to one JSONL file per model.

Usage:
    python 4_vqa_inference/run_vqa.py --benchmark benchmark.jsonl
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
MODELS = ("medgemma:4b", "medgemma1.5:4b", "qwen2.5vl:7b")
# Same options for every model and configuration: greedy decoding, at most 1024 new tokens.
INFERENCE_OPTIONS = {"num_gpu": 999, "num_predict": 1024, "temperature": 0.0}


def text_sha(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def read_jsonl(path):
    with Path(path).open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def load_configurations(path, selected=None):
    """Return {(strategy, framing): system prompt}, optionally restricted to 'strategy/framing' names."""
    strategies = yaml.safe_load(Path(path).read_text(encoding="utf-8"))["strategies"]
    configs = {(s, f): prompt for s, spec in strategies.items() for f, prompt in spec["prompts"].items()}
    if selected:
        wanted = [tuple(name.split("/")) for name in selected]
        unknown = [w for w in wanted if w not in configs]
        if unknown:
            raise ValueError(f"Unknown configurations: {unknown}")
        configs = {w: configs[w] for w in wanted}
    return configs


def load_questions(path, enriched_path=None):
    """Question text sent to the model; enriched questions replace it but keep the original for judging."""
    questions = {qid: q["question"] for qid, q in
                 yaml.safe_load(Path(path).read_text(encoding="utf-8"))["questions"].items()}
    if not enriched_path:
        return {qid: {"question": text, "original_question": text} for qid, text in questions.items()}
    enriched = yaml.safe_load(Path(enriched_path).read_text(encoding="utf-8"))["preguntas"]
    sent = {}
    for qid, entry in enriched.items():
        if entry["pregunta_original"] != questions[qid]:
            raise ValueError(f"Enriched question {qid} does not match the original question")
        sent[qid] = {"question": entry["prompt_enriquecido"], "original_question": questions[qid]}
    return sent


def build_tasks(pairs, questions, configs):
    tasks = []
    for pair in pairs:
        if pair["question_id"] not in questions:
            continue
        question = questions[pair["question_id"]]
        for (strategy, framing), system_prompt in configs.items():
            tasks.append({
                "image_id": pair["image_id"], "image": pair["image"], "question_id": pair["question_id"],
                "strategy": strategy, "framing": framing,
                "system_prompt": system_prompt, "prompt_sha256": text_sha(system_prompt),
                "question": question["question"], "question_sha256": text_sha(question["question"]),
                "original_question": question["original_question"],
            })
    return tasks


def ask(client, model, task, image_bytes):
    start = time.monotonic()
    response = client.chat(
        model=model,
        messages=[{"role": "system", "content": task["system_prompt"]},
                  {"role": "user", "content": task["question"], "images": [image_bytes]}],
        options=dict(INFERENCE_OPTIONS), keep_alive="20m",
    )
    return response["message"]["content"].strip(), round(time.monotonic() - start, 2)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--benchmark", type=Path, required=True,
                        help="JSONL with one documented image-question pair per line (see the README).")
    parser.add_argument("--image-root", type=Path, help="Folder that image paths are relative to "
                        "(default: the benchmark file's folder).")
    parser.add_argument("--questions", type=Path, default=ROOT / "questions/questions.yaml")
    parser.add_argument("--enriched-questions", type=Path,
                        help="Send the enriched questions instead (use with --configs direct_answering/direct_command).")
    parser.add_argument("--strategies", type=Path, default=HERE / "prompt_strategies.yaml")
    parser.add_argument("--configs", nargs="*", help="Subset of configurations as strategy/framing (default: all 15).")
    parser.add_argument("--model", action="append", help=f"Ollama model tag; repeatable (default: {', '.join(MODELS)}).")
    parser.add_argument("--output-dir", type=Path, default=Path("results/vqa"))
    return parser.parse_args()


def main():
    args = parse_args()
    pairs = read_jsonl(args.benchmark)
    image_root = args.image_root or args.benchmark.parent
    tasks = build_tasks(pairs, load_questions(args.questions, args.enriched_questions),
                        load_configurations(args.strategies, args.configs))
    import ollama
    client = ollama.Client(host=os.getenv("OLLAMA_HOST", "http://localhost:11434"), timeout=600)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for model in args.model or MODELS:
        output = args.output_dir / (model.replace("/", "_").replace(":", "_") + ".jsonl")
        with output.open("w", encoding="utf-8") as stream:
            for task in tasks:
                image_bytes = (image_root / task["image"]).read_bytes()
                response, seconds = ask(client, model, task, image_bytes)
                row = {k: v for k, v in task.items() if k not in ("system_prompt", "image")}
                row.update(model=model, response=response, processing_time_sec=seconds,
                           inference_options=INFERENCE_OPTIONS)
                stream.write(json.dumps(row, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
