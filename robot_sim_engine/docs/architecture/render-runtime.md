---
owner: architecture
audience: contributor
status: canonical
source_of_truth: manual
last_reviewed: 2026-04-17
---
# Render Runtime

## 目标

render 子系统当前不再只输出“能不能画出来”的隐含状态，而是把：

- capability downgrade
- runtime status
- telemetry events
- operation spans
- sampling counters
- backend-specific performance telemetry

统一沉入共享状态真源，供 UI、diagnostics、export 与质量门禁消费。

## 状态真源

- `SessionState.render_runtime`
- `SessionState.render_telemetry`
- `SessionState.render_operation_spans`
- `SessionState.render_sampling_counters`
- `SessionState.render_backend_performance`

## 服务边界

- `RenderTelemetryService`：写入与聚合 render telemetry
- `RenderStateSegmentStore`：只刷新 render 分段订阅，避免全局 selector 热路径回流
- diagnostics / export / status-panel：都从共享 render telemetry 真源消费

## 语义约束

- `scene_3d / plots / screenshot` 的 runtime capability 必须进入共享状态，而不是只停留在 placeholder 或日志层
- `render_runtime.screenshot` 必须同时暴露 `level / provenance`
- live capture 与 snapshot fallback 不允许伪装成同一种能力

## 验证

- `python scripts/verify_gui_smoke.py`
- render snapshot regression fixtures
- render telemetry 相关单元 / 回归测试
