# Questions

- [`questions.yaml`](questions.yaml): the 16 benchmark questions of Table 1, as sent to the
  models and to the judge, with an English translation for reference. The laterality reference
  comes from the image-upload metadata; every other reference comes from the report.
- [`enriched_questions.yaml`](enriched_questions.yaml): the enriched version of each question
  (visual features to inspect, hypothetical positive and negative examples and the expected
  answer format), identical for every image. The model receives `prompt_enriquecido` instead of
  the question; the judge receives `pregunta_original`.
