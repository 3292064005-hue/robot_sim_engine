# Compatibility Downstream Inventory

This document records the **audited downstream inventory** for retained compatibility surfaces in V7.2.

## Scope

The source of truth is `configs/compatibility_downstream_inventory.yaml`.

Each surface records:

- concrete in-repo downstream consumers that still exercise the compatibility path;
- an explicit out-of-tree audit result (`audited_absent` or `confirmed`);
- evidence paths used for that audit.

## Current audit result

As of **2026-04-14**, all retained compatibility surfaces have concrete in-repo downstream consumers recorded in `configs/compatibility_downstream_inventory.yaml`.

Out-of-tree downstream inventory was audited against:

- packaged entrypoints in `pyproject.toml`;
- checked-in user-facing docs such as `README.md` and `docs/stable_surface_migration.md`;
- compatibility governance docs in `docs/compatibility_support_boundary.md`.

For this release, the audited result is **no confirmed out-of-tree compatibility-only consumer** for any retained compatibility surface.

## Interpretation

This is stronger than a pure support-boundary statement:

1. retained compatibility surfaces still have concrete downstream callers that must be migrated before removal;
2. the repository now carries an auditable record of those callers;
3. out-of-tree consumers are not treated as "unknown" — they are explicitly audited and must be entered in the inventory before the verifier will accept them as confirmed.
