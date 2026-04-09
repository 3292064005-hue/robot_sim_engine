# Kinematics and trajectory conventions

- `world`: global visualization / scene frame.
- `base`: robot base frame (`RobotSpec.base_T`).
- `tool`: tool flange transform (`RobotSpec.tool_T`).
- `Pose` is the stable application/runtime pose surface. `Transform` is the homogeneous-matrix contract used for compose / inverse / rigid validation.
- FK results are interpreted as world/base-aligned homogeneous transforms produced from the configured serial chain.
- GUI input may use Euler / rotation-vector forms, but solver internals use matrix / rotation-vector errors.
- Trajectory quality metrics distinguish:
  - `goal_*_error`: final sample versus requested goal pose.
  - `start_to_end_*_delta`: realized motion between the first and last sample.
- `urdf_model` preserves serial URDF joint/link semantics and exposes geometry/collision availability through `RobotSpec.source_model_summary`.
- `urdf_skeleton` import is intentionally approximate: URDF joint origins are collapsed into a DH-like serial chain for demos/tests and are not a general URDF tree implementation.
