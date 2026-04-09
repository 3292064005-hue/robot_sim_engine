# Kinematics and trajectory conventions

- `world`: global visualization / scene frame.
- `base`: robot base frame (`RobotSpec.base_T`).
- `tool`: tool flange transform (`RobotSpec.tool_T`).
<<<<<<< HEAD
- `Pose` is the stable application/runtime pose surface. `Transform` is the homogeneous-matrix contract used for compose / inverse / rigid validation.
=======
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
- FK results are interpreted as world/base-aligned homogeneous transforms produced from the configured serial chain.
- GUI input may use Euler / rotation-vector forms, but solver internals use matrix / rotation-vector errors.
- Trajectory quality metrics distinguish:
  - `goal_*_error`: final sample versus requested goal pose.
  - `start_to_end_*_delta`: realized motion between the first and last sample.
<<<<<<< HEAD
- `urdf_model` preserves serial URDF joint/link semantics and exposes geometry/collision availability through `RobotSpec.source_model_summary`.
=======
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
- `urdf_skeleton` import is intentionally approximate: URDF joint origins are collapsed into a DH-like serial chain for demos/tests and are not a general URDF tree implementation.
