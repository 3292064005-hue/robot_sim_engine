# Planning Scene / ACM

`PlanningScene` 现已进入当前工程的**stable scene surface**，作为环境障碍物、允许碰撞矩阵（ACM）与 scene revision 的统一 authority，并持续服务于校验、导出、session 与 stable scene toolbar/editor。

当前稳定能力范围：

- 环境障碍物与 attached objects 现在支持 `box / sphere / cylinder` 三类稳定 primitive；校验真源仍统一收口为 `AABB` authority，以保证验证/导出/session 语义一致，但 stable scene summary 现在会同时保留声明几何与解析几何
- `AllowedCollisionMatrix` 可显式声明 link-link 或 link-object 的 ignore pairs
- `ValidateTrajectoryUseCase` 可接受 `planning_scene`，并输出：
  - `scene_revision`
  - `collision_level`
  - `ignored_pairs`
  - `self_pairs`
  - `environment_pairs`
- session / export 路径会保留 `planning_scene` 的稳定摘要信息（`revision`、`collision_backend`、`obstacle_ids`、`attached_object_ids`、`allowed_collision_pairs`、`geometry_source`、`scene_authority`、`scene_fidelity` 等字段）；运行时附加摘要单独写入 `scene_runtime_summary`，不再混入 `planning_scene`

当前 stable 主链已补齐 authority 与编辑面：

- 机器人加载 / 导入 / 编辑保存后，运行时会自动重建一份 canonical `planning_scene`
- stable 主窗口会投影 scene backend / revision / obstacle / pair 摘要
- stable `SceneToolbar` 现通过结构化 scene editor 提供 `box / sphere / cylinder` primitive、attached object 与 allowed collision pairs 的编辑入口
- `SceneAuthorityService` 统一管理 scene bootstrap、障碍物 ID 策略、ACM 写入与 scene metadata；scene summary 现显式输出 `scene_geometry_contract`、对象级 `declared_geometry` / `resolved_geometry`
- AABB collision backend 仍是默认稳定后端；更高保真 backend 仍未形成产品化承诺

当前仍不包含：

- 连续碰撞检测
- FCL / mesh 级精确碰撞
- 完整 attached-object authoring
- 多 collision backend 的完整产品化切换
