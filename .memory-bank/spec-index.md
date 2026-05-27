---
description: SDD Design Specs Index and route map for source-of-truth documents.
status: active
---
# SDD Design Specs Index

## Purpose
- Use this file as the route map for SDD design specs and explicit normative docs.
- Read this index before creating new specs or doing serious T2/T3 work.
- If a design area is not needed, mark it `not_applicable` with a short reason.
- Do not create authoritative specs unless PRD/user/spec evidence contains the decision.

## Hard rules
- Do not create a new spec before checking existing specs through this index.
- `/spec-init` may mark areas as planned/candidate/unknown/not_applicable, but must not invent authoritative architecture/contracts/states/data specs.
- `/spec-design FT-<NNN>` owns feature-level design before `/prd-to-tasks FT-<NNN>`.
- `T2` / `T3` tasks must carry relevant linked specs in task richer fields.

## Existing authoritative specs
- [.memory-bank/glossary.md](glossary.md): Термины и agreed vocabulary.
- [.memory-bank/invariants.md](invariants.md): Глобальные MUST/NEVER правила.
- [.memory-bank/constitution.md](constitution.md): Top governing policy for AI-first project decisions.
- [.memory-bank/contracts/](contracts/): Контракты интерфейсов и boundary specs.
- [.memory-bank/domains/](domains/): Domain/data model specs.
- [.memory-bank/states/](states/): Lifecycle/state rules.
- [.memory-bank/runbooks/](runbooks/): Operational procedures.
- [.memory-bank/testing/index.md](testing/index.md): Verification basis и quality gates.

## Planned design areas
- TBD

## Candidate design areas
- TBD

## Unknown design areas
- TBD

## Not applicable areas
- TBD

## Feature design status map
| Feature | spec_design_status | Linked specs | Notes |
|---|---|---|---|
| FT-XXX | unknown | - | Fill via /spec-design or /spec-auto |

## Expected spec locations
- Feature hubs: `.memory-bank/tech-specs/FT-<NNN>-<slug>.md`
- Architecture notes: `.memory-bank/architecture/<topic>.md`
- Contracts: `.memory-bank/contracts/<boundary>.md`
- Domain/data models: `.memory-bank/domains/<domain>.md`
- States: `.memory-bank/states/<lifecycle>.md`
- ADRs: `.memory-bank/adrs/ADR-<NNN>-<slug>.md`
- Testing/runbooks: `.memory-bank/testing/` and `.memory-bank/runbooks/`

## Gaps and open questions
- TBD

## Compatibility note
- Duo docs в `architecture/` и `guides/` остаются валидными.
- Этот слой уточняет source-of-truth, а не отменяет duo docs.
