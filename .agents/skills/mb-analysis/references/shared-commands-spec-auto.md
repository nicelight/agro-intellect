---
description: Autonomous SDD Design Specs workflow for spec-index initialization and feature design.
status: active
---
# /spec-auto - Autonomous SDD design

<objective>
Run the autonomous equivalent of `/spec-init` and `/spec-design` without user interview.

Supported arguments:
- `--init`
- `FT-<NNN>`
- `--all`
</objective>

<process>

## 0) Mode
`/spec-auto` never asks the user questions.

It asks and answers internal design questions itself, records assumptions, and makes conservative/KISS decisions from:
- `.memory-bank/constitution.md`
- `.memory-bank/analysis/product-brief.md`
- `.memory-bank/prd.md`
- `.memory-bank/spec-index.md`
- `.memory-bank/requirements.md`
- `.memory-bank/epics/`
- `.memory-bank/features/`
- existing specs

If a contradiction or ambiguity is unsafe/blocking, record a blocker and stop with the terminal state expected by the active autonomous workflow.

## 1) Arguments
- `--init`: run autonomous spec-index initialization after `/write-prd` and before `/prd`
- `FT-<NNN>`: run autonomous feature-level design for one feature after `/prd`
- `--all`: run autonomous feature-level design for every targeted feature after `/prd`

If no argument is provided, infer:
- before `/prd`, use `--init`
- after `/prd`, use `--all`; if shared concerns exist, run `/spec-backbone --all` first
- if unclear, stop and report the missing argument

## 2) `--init`
Perform `/spec-init` behavior without interview:
- read Constitution, Product Brief, PRD, existing spec-index, and existing specs
- update `.memory-bank/spec-index.md` as SDD Design Specs Index / route map
- mark areas as planned/candidate/unknown/not_applicable
- record assumptions and open questions
- do not create authoritative design specs unless PRD/user evidence already contains the decision

If the skeleton would be misleading without unavailable user input:
- record `BLOCKER: misleading spec-index risk`
- in autonomous flow set terminal state `HALT_BLOCKING_QUESTIONS`
- stop before `/prd`

## 3) `FT-<NNN>` and `--all`
For each targeted feature:
1. Read `.memory-bank/spec-index.md` and relevant existing specs first.
2. Check whether the feature is simple enough for `spec_design_status: not_required`.
3. If design is needed, update only the minimal necessary artifacts.
4. Update `.memory-bank/spec-index.md`.
5. Update target feature frontmatter with `spec_design_status` and `spec_design_links`.

Autonomous decision rules:
- prefer existing specs over new files
- choose the smallest reversible design that satisfies PRD/Constitution/requirements
- record assumptions in the feature design hub or spec-index
- do not invent external contracts, security posture, migrations, or irreversible data behavior
- set `spec_design_status: complete` only when every feature-relevant SDD design area either has a concrete linked spec file routed through `.memory-bank/spec-index.md` as an authoritative, evidence-backed source of truth, or is explicitly `not_applicable` for this feature
- do not set `complete` while any feature-relevant design area remains planned, candidate, unknown, conflicting, or otherwise unresolved; instead set `spec_design_status: blocked` or leave the feature without `complete`, and record the gap/open question in `.memory-bank/spec-index.md`
- if blocking ambiguity affects security/compliance/payments/external contracts/data loss, set `spec_design_status: blocked`, record the reason, and halt the autonomous run with `HALT_BLOCKING_QUESTIONS` or `HALT_CLARIFICATION_REQUIRED`

For simple T0/T1-like features, `not_required` is valid with a concise rationale.

## 4) Required outputs
For `--init`:
- `.memory-bank/spec-index.md`

For feature design:
- target feature docs updated with `spec_design_status`
- linked specs when required
- `.memory-bank/spec-index.md` updated

For `--all`:
- all targeted features have `spec_design_status: complete|not_required|blocked`
- no `/prd-to-tasks --all` handoff if any targeted feature is `blocked`

## 5) Handoff
Report:
- mode and targeted features
- specs created/updated
- assumptions
- blockers
- whether the next command is `/prd`, `/prd-to-tasks FT-<NNN>`, or `/prd-to-tasks --all`

</process>
