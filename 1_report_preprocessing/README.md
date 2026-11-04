# Report preprocessing

Each study has one report for both eyes. Every report was sent to an LLM (Gemini 3.1 Pro) with
[`split_by_eye_prompt.txt`](split_by_eye_prompt.txt) to obtain one text per eye. The prompt only
allows copying sentences of the original report; sentences about both eyes are adapted to one
eye, and general impressions and recommendations are copied to both. Each eye-specific text is
then attached to the photograph of that eye.
