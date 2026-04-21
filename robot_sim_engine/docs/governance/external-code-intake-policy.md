---
owner: governance
audience: maintainer
status: canonical
source_of_truth: manual
last_reviewed: 2026-04-17
---
# External code intake policy

## Allowed intake modes

### 1. White-list migration
Only permissive-license sources may be copied or closely adapted into this
repository.

Accepted families:
- MIT
- BSD-2-Clause / BSD-3-Clause
- Apache-2.0

Requirements:
- preserve upstream copyright / license notices when code is copied
- register the source in `THIRD_PARTY_NOTICES.md`
- document the intake in commit history and release notes when user-facing
  behavior changes

### 2. Black-box reimplementation
Any external project may be used as a behavioral or architectural benchmark
without copying implementation.

Allowed references:
- public documentation
- public APIs
- algorithm papers
- benchmark behavior
- test semantics

Forbidden behavior:
- copying code from projects whose licenses are absent, incompatible, or
  otherwise unclear

## Intake checklist
1. Confirm upstream license.
2. Classify the intake as migration or black-box reimplementation.
3. Record the source in `THIRD_PARTY_NOTICES.md`.
4. Update tests / docs / runtime contracts together with the code change.
5. Keep a rollback path for replaced modules.
