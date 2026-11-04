# LLM-as-a-judge

[`judge.py`](judge.py) scores every answer against its reference with GPT-6 Luna through Codex
CLI (medium reasoning effort). The judge receives the general rubric and the guide of the
question ([`judge_prompt.yaml`](judge_prompt.yaml)), the original question, the reference answer
and up to 15 candidate answers of the same image–question pair, in a seeded random order. It
does not see the report, the image or which model or configuration produced each answer.

Scores: 1 when the answer agrees with every aspect of the reference; 0.5 when it answers part
of it without contradicting it, or reports the same finding with a different certainty; 0 for
contradictions, unrelated answers and abstentions. Laterality only admits 0 or 1. The output
must follow [`output_schema.json`](output_schema.json) (one `slot`, `score` and `explanation`
per candidate).
