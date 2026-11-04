# Report-Grounded Visual Question Answering on Fundus Photographs

Prompts, questions and code for the paper *Report-Grounded Visual Question Answering: A
Framework for Evaluating Multimodal Models on Fundus Photographs* (F. J. Arellano and
J. I. Orlando, submitted to ISBI 2027).

The framework turns routine ophthalmological reports into a fixed set of questions, builds
evidence-grounded reference answers from each report (or marks the question as *not
documented*), asks multimodal LLMs (MLLMs) the documented questions from the image alone,
and scores their free-text answers against the references with an LLM judge.

**Data availability.** The fundus photographs, reports, reference answers, model answers and
judge scores come from a private screening program and are not released. This repository
contains the prompts of every step, the 16 questions and the code.

## Contents

| Paper (Sec. 2) | Folder | What is there |
| --- | --- | --- |
| Report preprocessing | [`1_report_preprocessing/`](1_report_preprocessing/) | Prompt that splits each study report into one text per eye. |
| Clinical question discovery | [`2_question_discovery/`](2_question_discovery/) | Orchestrator and sub-agent prompts that discover questions from batches of reports. |
| Benchmark questions (Table 1) | [`questions/`](questions/) | The 16 questions (Spanish, with English translation) and their enriched versions. |
| Reference answer generation | [`3_reference_generation/`](3_reference_generation/) | Extractor, reviewer and orchestrator prompts, interpretation rules and the helper with the deterministic checks. |
| Experimental setup | [`4_vqa_inference/`](4_vqa_inference/) | The 15 prompting configurations and the inference script (Ollama). |
| LLM-as-a-judge evaluation | [`5_llm_judge/`](5_llm_judge/) | Judge rubric with the question-specific guides, output schema and runner (Codex CLI). |
| Metrics (Sec. 2.3, 3) | [`6_analysis/`](6_analysis/) | Mean scores, best configuration, sensitivity-/specificity-like and balanced scores, patient-level bootstrap, question enrichment, example copying. |
| Human validation (Sec. 3.1) | [`7_human_validation/`](7_human_validation/) | Sampling strata and the weighting behind the reported agreement. |

The prompts are in Spanish, the language of the reports, and are the exact texts used.

## Models

| Role | Model | How it was run |
| --- | --- | --- |
| Report preprocessing, question discovery | Gemini 3.1 Pro | Discovery: orchestrator with sub-agents in Antigravity, batches of 10 reports. |
| Reference answer generation | GPT-6 Luna | Codex CLI; extractor with low and reviewer with high reasoning effort. |
| LLM judge | GPT-6 Luna | Codex CLI 0.162.1, medium reasoning effort, batches of up to 15 answers. |
| Evaluated MLLMs | MedGemma 4B, MedGemma 1.5 4B, Qwen2.5-VL 7B | Ollama tags `medgemma:4b`, `medgemma1.5:4b`, `qwen2.5vl:7b` (4-bit, Q4_K_M); temperature 0, at most 1,024 new tokens. |

## Benchmark file

The scripts read one JSON object per line, one per documented image–question pair. Pairs whose
question the report does not document are not in the file: they are never asked.

```json
{"image_id": "img-001", "patient_id": "p-001", "image": "images/img-001.png",
 "question_id": "CAT_RETINOPATIA_DIABETICA:3", "reference": "Exudados duros temporales a la mácula.",
 "evidence": ["Exudados duros temporales a la mácula."]}
```

`patient_id` is used only for the patient-level bootstrap. `evidence` holds the verbatim
quotations from the eye-specific report; the judge receives `reference` only.
