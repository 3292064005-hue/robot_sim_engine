# Architecture

## Layers

- `model`: immutable data models
- `core`: pure math kernels
- `application`: DTO / use cases / workers
- `presentation`: Qt controller and widgets
- `render`: PyVista / pyqtgraph adapters
- `infra`: logging and file utilities

## Rules

1. `core` cannot import Qt.
2. Long-running work must run in worker threads.
3. FK / Jacobian / IK / Trajectory must be test-covered.
4. Euler angles may be used in UI only, not in the IK core.
