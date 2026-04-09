# Capability Matrix

## scene_features
- `planning_scene` [stable]
  - owner: `collision.scene`
  - active_backends: `['aabb']`
  - declared_backends: `['aabb', 'capsule']`
  - edit_surface: `stable_scene_editor`
  - experimental_backends: `['capsule']`
  - fallback_backend: `aabb`
  - integration_scope: `validation_export_session_scene_toolbar`
  - ui_surface: `stable_scene_toolbar`
- `collision_backend_aabb` [internal]
  - owner: `collision.scene`
  - availability: `enabled`
  - backend_id: `aabb`
  - fallback_backend: `aabb`
  - family: `broad_phase`
  - required_dependencies: `[]`
  - supported_collision_levels: `['aabb']`
- `collision_backend_capsule` [experimental]
  - owner: `collision.scene`
  - availability: `disabled_by_profile`
  - backend_id: `capsule`
  - fallback_backend: `aabb`
  - family: `narrow_phase`
  - required_dependencies: `[]`
  - supported_collision_levels: `['capsule']`
