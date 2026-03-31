Patch Notes - Optimized V1
==========================

1. Added playback subsystem
   - PlaybackState extended with speed multiplier and loop policy
   - PlaybackService / StepPlaybackUseCase / PlaybackWorker added
   - PlaybackPanel now supports play, pause, step, stop, seek, speed, loop

2. Controller and state flow hardened
   - Centralized state access through StateStore
   - Trajectory planning and playback now update SessionState consistently
   - Session export and trajectory export integrated into controller

3. Render and plots improved
   - Scene3DWidget now supports playback marker updates
   - SceneController caches end-effector path and updates trajectory visuals
   - PlotsManager supports persistent cursors for playback sync

4. Robot configuration and registry improved
   - RobotSpec now supports display_name, description, metadata
   - RobotRegistry preserves stored id vs display name and metadata roundtrip
   - RobotConfigPanel can save edited DH rows and home_q

5. Validation and metrics improved
   - InputValidator clamps joint goals and validates home_q vs limits
   - MetricsService summarizes trajectory statistics in addition to IK metrics

6. Test suite expanded
   - Added playback, validator, metadata roundtrip, and trajectory metrics tests
