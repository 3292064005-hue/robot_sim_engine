# Legacy controller compatibility surface

These wrappers are frozen compatibility shims. Canonical GUI/application flows must use the
workflow services mounted by `main_controller_support.py`. New runtime fields, execution-level
contracts, environment contracts, and export schema changes must land on the workflow/application
surfaces first and may only be mirrored here when required for narrow downstream adapters or
compatibility tests.
