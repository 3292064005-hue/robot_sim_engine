# Compatibility Support Boundary

Retained compatibility surfaces in this repository are **internal transitional adapters**, not an externally supported extension contract.

## Audited downstream inventory

The authoritative downstream inventory now lives in `configs/compatibility_downstream_inventory.yaml` and is mirrored into the retirement plan in `configs/compatibility_retirement.yaml`.

For V7.2 that inventory records two facts separately:

1. concrete in-repo downstream consumers that still exercise each compatibility surface;
2. the audited out-of-tree result for the same surface (`audited_absent` or `confirmed`).

## Out-of-tree policy

Out-of-tree compatibility consumers are **not a supported extension contract**. The release process therefore treats any out-of-tree use as an explicit audited inventory event rather than as silent observational ambiguity.

This means:

1. no retained compatibility surface may ship with an unspecified out-of-tree state;
2. `python scripts/verify_compatibility_retirement.py` rejects retirement entries that drift from the audited downstream inventory;
3. if an out-of-tree compatibility consumer is ever confirmed, it must be recorded in `configs/compatibility_downstream_inventory.yaml` and mirrored into `configs/compatibility_retirement.yaml` with concrete evidence before the plan can validate again.

## Migration rule

External integrations must target canonical workflow services, typed descriptors, and public APIs rather than deprecated compatibility aliases.

## Rollback rule

If a release needs to keep a confirmed out-of-tree compatibility consumer for one more cycle, that consumer must stay in the audited downstream inventory with concrete evidence and an explicit removal plan.
