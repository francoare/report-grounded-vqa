# Reference answer generation

The question schema is applied to every eye-specific report, one category at a time, by three
LLM roles running in Codex CLI (GPT-6 Luna):

1. **Extractor** ([`extractor.md`](extractor.md), low reasoning effort): answers each question of
   the category from the report alone, with verbatim quotations as evidence, or returns `null`
   (*not documented*). It preserves negations, uncertainty and partial answers and never fills in
   what the report does not say.
2. **Reviewer** ([`reviewer.md`](reviewer.md), high reasoning effort): checks every candidate
   against the report and accepts, corrects or escalates it.
3. **Orchestrator** ([`orchestrator.md`](orchestrator.md)): prepares each sub-agent message with
   [`helper.py`](helper.py), adjudicates flagged answers and approves those supported by the
   evidence.

[`helper.py`](helper.py) never calls a model. `build_message` assembles what each sub-agent
receives. The deterministic checks reject outputs with the wrong structure, missing or
duplicated questions, quotations that do not occur verbatim in the report, answers without
evidence (or evidence without an answer) and answers that drop the uncertainty of their
evidence (`analyze_output`, `extraction_errors`, `adjudicate_finding`). Cases left unresolved
are excluded from the benchmark. The question-specific interpretation rules are in
[`interpretation_rules.json`](interpretation_rules.json).
