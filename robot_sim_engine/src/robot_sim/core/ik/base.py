from __future__ import annotations
<<<<<<< HEAD

from typing import Callable, Protocol

from robot_sim.domain.types import FloatArray
from robot_sim.model.ik_result import IKIterationLog, IKResult
from robot_sim.model.pose import Pose
from robot_sim.model.robot_spec import RobotSpec
from robot_sim.model.solver_config import IKConfig


class InverseKinematicsSolver(Protocol):
    """Runtime contract implemented by all IK solvers.

    The contract intentionally preserves the stable V7 call signature so
    existing solver implementations remain valid while higher layers enrich the
    request semantics through :class:`robot_sim.application.dto.IKRequest`.
    """

=======
from typing import Callable, Protocol
from robot_sim.model.robot_spec import RobotSpec
from robot_sim.model.pose import Pose
from robot_sim.model.solver_config import IKConfig
from robot_sim.model.ik_result import IKIterationLog, IKResult
from robot_sim.domain.types import FloatArray

class InverseKinematicsSolver(Protocol):
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
    def solve(
        self,
        spec: RobotSpec,
        target: Pose,
        q0: FloatArray,
        config: IKConfig,
        cancel_flag: Callable[[], bool] | None = None,
        progress_cb: Callable[[IKIterationLog], None] | None = None,
<<<<<<< HEAD
        **kwargs,
    ) -> IKResult:
        """Solve a task-space request.

        Args:
            spec: Canonical robot specification.
            target: Requested end-effector pose.
            q0: Initial seed vector.
            config: Solver runtime configuration.
            cancel_flag: Optional cooperative cancellation callback.
            progress_cb: Optional per-iteration progress callback.
            **kwargs: Solver-specific extensions such as ``attempt_idx``.

        Returns:
            IKResult: Bounded result contract describing success/failure,
                diagnostics, and residuals.
        """
=======
    ) -> IKResult:
>>>>>>> 3ed78e647985c6d680c085e4480d898855278db3
        ...
