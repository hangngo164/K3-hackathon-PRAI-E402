# Quiz prompt v1

Generate a JSON payload with quiz items based on the selected slide text scope.

Each item must include:
- item_id
- type
- stem
- options
- answer_index
- answer_text
- explanation
- anchor
- difficulty
- distractor_rationale

Constraints:
- Use only the provided text.
- Each anchor quote must match a substring from the source text.
- Do not produce trick meta questions or unrelated content.
