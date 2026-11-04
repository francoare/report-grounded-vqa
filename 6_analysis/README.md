# Metrics

[`metrics.py`](metrics.py) reproduces the numbers of the paper from the judge scores:

- mean score per model and configuration (Fig. 2a) and the best configuration of each model
  (highest mean over all documented pairs);
- mean score per question under the best configuration (Table 1);
- strategy and framing means, and the illumination question with and without few-shot prompting;
- DR findings by reference polarity: sensitivity-like (lesion documented as present) and
  specificity-like (documented as absent) mean scores, and the balanced score, the mean of both
  within each question averaged over the questions with at least 20 present and 20 absent
  references (Fig. 2b);
- question enrichment: differences against direct answering / direct command, paired within
  each bootstrap resample.
- with `--answers`: share of answers to documented lesions that deny them under the best
  configuration (`denies()`, a fixed rule on the answer text).

Polarity comes from a fixed rule on the reference text (`polarity()`); references with doubt,
such as "compatible con", count as present. 95% CIs come from a patient-level bootstrap
(2,000 resamples, seed 42), the same resamples for every group.

[`answer_copying.py`](answer_copying.py) counts answers that reuse example wording: the
"subexpuesta" (underexposed) illumination example of few-shot prompting, and the example
answers of each enriched question.
