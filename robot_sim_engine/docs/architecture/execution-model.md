---
owner: architecture
audience: contributor
status: canonical
source_of_truth: manual
last_reviewed: 2026-04-17
---
# Execution Model

## 任务生命周期

当前任务主线统一使用：

- `TaskState`
- `TaskSnapshot`
- structured worker lifecycle events
- `ThreadOrchestrator`

controller 负责构造 request，coordinator 负责编排 worker / thread / state 投影，GUI 线程不执行核心计算。

## Threading rules

1. `core` 禁止导入 Qt
2. IK / trajectory / benchmark / playback / export / screenshot 优先走 worker
3. GUI 线程只做参数收集、状态更新和渲染
4. 取消、停止、queue-latest、timeout 都必须通过统一 orchestrator 传播

## Worker contract

当前 canonical worker lifecycle surface 为：

- `progress_event`
- `finished_event`
- `failed_event`
- `cancelled_event`

worker lifecycle 不再保留 legacy signal mirror；新的 worker 必须直接实现 structured event surface。

## Coordinator dependency rule

- presentation object graph 由 `presentation.assembly.PresentationAssembly` 统一构建
- coordinator 构造必须显式注入依赖
- 禁止从 `MainWindow` / controller 猜 facade/threader
- `export` / `screenshot` 主链必须继续走 worker 生命周期

## Capture / screenshot path

- screenshot 主链经 `CaptureSceneUseCase` 收口
- `SceneCoordinator` 只负责 worker 编排、UI 投影和 telemetry 归档
- 不允许 coordinator 重新承担底层截图 service 语义
