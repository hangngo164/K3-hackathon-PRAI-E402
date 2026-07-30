# Summarize prompt v1

You are given a specific text scope extracted from slide content. Produce a JSON object with the following fields:

- scope_label
- tldr
- bullets
- key_terms
- not_covered
- confidence

Constraints:
- Use only the text provided.
- Each bullet must include an anchor with page_no, block_ids, and quote from the source.
- Preserve original terminology and do not translate English terms.
- Do not hallucinate facts that are not present in the scope text.
