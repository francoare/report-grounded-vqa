# Model inference

[`run_vqa.py`](run_vqa.py) sends each documented image–question pair to each model under each
configuration of [`prompt_strategies.yaml`](prompt_strategies.yaml): the configuration as the
system message, then the question and the image as the user message. The model never receives
the report or the reference. Answers are stored without post-processing.

```bash
# The 15 configurations (paper, Fig. 2a)
python 4_vqa_inference/run_vqa.py --benchmark benchmark.jsonl --output-dir results/vqa
# Enriched questions, direct answering / direct command
python 4_vqa_inference/run_vqa.py --benchmark benchmark.jsonl --output-dir results/vqa_enriched \
    --enriched-questions questions/enriched_questions.yaml --configs direct_answering/direct_command
```

Ollama options: `temperature 0`, `num_predict 1024` and `num_gpu 999` (all layers on the GPU).
MedGemma has no dedicated system role; its Ollama chat template places the system message
before the user turn.
