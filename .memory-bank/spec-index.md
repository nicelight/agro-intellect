---
description: Pure SDD spec registry and planned-spec index.
status: active
owner: architecture
last_updated: 2026-06-03
source_of_truth:
  - .memory-bank/constitution.md
  - .memory-bank/prd.md
  - .memory-bank/spec-backbone.md
---
# SDD Spec Index

## Purpose
- Keep a concise registry of existing and planned SDD specs.
- Read this index before creating new specs or doing serious T2/T3 work.
- Keep readiness, open design questions, backbone status, and routing handoffs in [.memory-bank/spec-backbone.md](spec-backbone.md).
- Feature `spec_design_status` lives in feature frontmatter, not in this index.

## Spec Registry
| Spec | Type | Path | Status | Owner command | Scope |
|---|---|---|---|---|---|
| Project Constitution | governance | [.memory-bank/constitution.md](constitution.md) | active | /constitution | Top governing policy. |
| Invariants | invariants | [.memory-bank/invariants.md](invariants.md) | active | /spec-init or /spec-design | Global MUST/NEVER rules. |
| Glossary | glossary | [.memory-bank/glossary.md](glossary.md) | active | /spec-init or /spec-design | Shared MVP v2 vocabulary. |
| User Scenarios | scenarios | [.memory-bank/user-scenarios.md](user-scenarios.md) | active | /spec-init | Primary actors, core scenarios, out-of-scope scenarios, and decomposition implications. |
| Core Domain | domain | [.memory-bank/domains/core-domain.md](domains/core-domain.md) | active | /spec-init | Main entities, roles, business rules, lifecycle hints, and decomposition constraints. |
| Boundary Map | boundary_hints | [.memory-bank/contracts/boundary-map.md](contracts/boundary-map.md) | active | /spec-init | Preliminary boundary hints only; no endpoints, schemas, or OpenAPI details. |
| Lifecycle Map | lifecycle_hints | [.memory-bank/states/lifecycle-map.md](states/lifecycle-map.md) | active | /spec-init | Lifecycle hints that affect epic/feature cuts. |
| Testing Index | testing | [.memory-bank/testing/index.md](testing/index.md) | planned | /prd or /spec-design | Verification strategy and quality gates. |

## Planned Specs
| Area | Expected path | Needed by | Notes |
|---|---|---|---|
| system_architecture | .memory-bank/architecture/system-architecture.md | /spec-design | Default global architecture hub after /prd. |
| feature_design | .memory-bank/tech-specs/FT-<NNN>-<slug>.md | /spec-improve | Feature-local specs only when needed before task decomposition. |

## Broken / Missing Links
- TBD

## Update Rules
- Keep this file as index/registry only: names, paths, statuses, owners, scopes, and broken links.
- Do not add global backbone status, backbone matrices, feature status maps, long hard rules, or open design question dumps here.
- Use [.memory-bank/spec-backbone.md](spec-backbone.md) for pre-PRD readiness, decomposition inputs, global backbone status, matrix, and handoffs.
- Use linked specs or ADRs for detailed decisions, rationale, contracts, state transitions, schemas, invariants, and testing rules.
