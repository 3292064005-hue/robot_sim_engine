# Roadmap

## Current: V7

<<<<<<< HEAD
### Shipped in V7

=======
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
- Registry / plugin contracts
- Package export
- URDF importer skeleton
- Waypoint / retiming groundwork
- Collision precheck groundwork
- Benchmark baseline compare
- GUI / benchmark / performance test layout
<<<<<<< HEAD
- 6R analytic IK plugin
- off-screen screenshot regression in CI / regression fixtures

### Completed through V7 hardening
=======

## Completed through V7
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3

- VersionCatalog and unified schema/version contract
- TaskSnapshot / task events / lifecycle-aware thread orchestration
- Importer registry split + RobotModelBundle + importer fidelity contract
- Trajectory validation split into dedicated validators
- Capability matrix / module status / V7 documentation alignment
<<<<<<< HEAD
- Render telemetry segmentation inside `StateStore` / `RenderTelemetryService`
- MainController bootstrap narrowed behind `PresentationBootstrapBundle`
- Packaged config staging from single-source `configs/`

## Next candidate: V8

- Redundant solver plugin
- richer waypoint graph editor
- scene picking to target pose
- URDF geometry + simple mesh visualization
- broader collision backend implementations beyond current AABB baseline
=======

## Next candidate: V8

- 6R analytic IK plugin
- Redundant solver plugin
- richer waypoint graph editor
- off-screen screenshot regression in CI
- scene picking to target pose
- URDF geometry + simple mesh visualization
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3

## Explicitly out of scope now

- rigid-body dynamics
- closed-loop control
- industrial controller SDK integration
- continuous collision detection
- high-fidelity physics simulation
