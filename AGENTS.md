# Notes for AI coding agents

## Comments

- Be concise. A comment should explain _why_ in a line or two, not narrate _what_ the code does.
- No multi-paragraph essays in code or CI config. For rationale, a short sentence plus an issue/PR reference is enough.
- Explain the code as it stands, not the change. No history ("used to", "before X",
  which incident prompted it): that belongs in the PR or commit description.
- Prefer a one-line comment to a docstring that only restates the function name.
- Match the brevity and style of the surrounding code.

## Changes

- Keep diffs minimal and focused on the task; don't refactor unrelated code.
- Prefer existing tools, helpers, and patterns over introducing new ones.
