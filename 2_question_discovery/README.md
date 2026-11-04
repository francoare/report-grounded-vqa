# Clinical question discovery

An orchestrating LLM ([`orchestrator.md`](orchestrator.md)) splits each batch of eye-specific
reports into sub-batches of 10 and sends each to a sub-agent ([`subagent.md`](subagent.md))
together with the questions found so far. The sub-agent returns general questions with the
specific observations needed to answer them, reusing or extending existing questions instead
of creating near-duplicates. The paper used Gemini 3.1 Pro in Antigravity (`define_subagent`
and `write_to_file` are Antigravity tools); `<workdir>` is the working folder.

The discovered questions were then grouped into clinical categories and their wording was
refined manually. The 16 questions of the two evaluated categories are in
[`../questions/questions.yaml`](../questions/questions.yaml).
