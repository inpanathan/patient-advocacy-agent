---
name: spec
description: Interview the user about a feature, then write a complete specification to docs/specs/
disable-model-invocation: true
argument-hint: "[feature-name]"
---

Create a detailed feature specification for: $ARGUMENTS

## Phase 1: Interview

Use the AskUserQuestion tool to interview the user. Ask about:

1. **Core behavior**: What exactly should this feature do? What are the inputs and outputs?
2. **User interaction**: Who uses this and how? What triggers it?
3. **Technical constraints**: Any required libraries, performance targets, or compatibility needs?
4. **Edge cases**: What happens with invalid input, empty data, timeouts, or concurrent access?
5. **Scope boundaries**: What is explicitly NOT part of this feature?

Keep interviewing until the feature is well-defined. Don't ask obvious questions — dig into the hard parts.

## Phase 2: Write spec

After the interview, write the spec to `docs/specs/$ARGUMENTS.md` using the template at `docs/templates/spec_template.md`.

Fill in every section with concrete details from the interview. Include:
- Specific Pydantic model definitions where relevant
- Actual endpoint paths and methods
- Real error codes from `ErrorCode` enum
- Concrete test scenarios, not generic placeholders

## Phase 3: Next steps

After writing the spec, tell the user:
1. Review and edit the spec at `docs/specs/$ARGUMENTS.md`
2. Start a fresh Claude session to implement it with clean context
3. Reference the spec: `Implement the feature described in @docs/specs/$ARGUMENTS.md`
