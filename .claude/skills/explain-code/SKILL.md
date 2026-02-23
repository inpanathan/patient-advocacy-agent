---
name: explain-code
description: Explain how code works using analogies, ASCII diagrams, and step-by-step walkthroughs. Use when asked "how does this work?" or "explain this code".
context: fork
agent: Explore
allowed-tools: Read, Grep, Glob
---

Explain the code specified by $ARGUMENTS.

Follow this structure:

1. **Analogy**: Compare the code to something from everyday life to build intuition

2. **Diagram**: Draw an ASCII diagram showing the flow, structure, or relationships:
   ```
   [Input] → [Processing] → [Output]
       ↓
   [Side effect]
   ```

3. **Walkthrough**: Explain step-by-step what happens when the code runs:
   - What triggers it
   - What data flows through it
   - What decisions it makes
   - What it produces

4. **Key detail**: Highlight one non-obvious behavior, gotcha, or design decision that someone new to this code should know

Keep explanations conversational. Use the actual function/variable names from the code.
