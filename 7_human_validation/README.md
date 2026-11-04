# Human validation

One author reviewed two stratified samples, with text only (no images).

**References.** 120 references compared with the eye-specific report text: 65 lesion
references (15 present with doubt, 25 present, 25 absent), 25 image-quality references and
30 *not documented* labels (15 lesion, 15 image quality). Laterality, which comes from
metadata, was not sampled. Each reference was marked correct or incorrect.

**Judge.** 100 judge scores rescored on the same 0 / 0.5 / 1 scale without seeing the judge's
score, explanation or the model: 79 from the original questions and 21 from the enriched
questions, stratified by judge score (more 0.5 scores than in the benchmark) and balanced by
model and category. Laterality was not sampled.

**Weighting.** Because the strata were sampled at different rates, every reported percentage
is weighted to the benchmark: each sampled item weighs (stratum size in the benchmark) /
(items sampled from that stratum). For references, the 89% covers the lesion and image-quality
references (958 and 1,069 in the benchmark); *not documented* labels are reported apart. For the
judge, the 88% weights each judge-score stratum by its frequency among the judge's scores
(laterality excluded); the unweighted agreement in the sample was 80%. 95% CIs come from 2,000
bootstrap resamples within strata (seed 42; one generator for all intervals, drawn in this
order: documented references, *not documented* labels, judge). [`weighting.py`](weighting.py)
contains these computations, the linearly weighted kappa and the stratum sizes.
