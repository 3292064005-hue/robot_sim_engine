class RobotSimError(Exception):
    """Base error for the simulator."""

class ValidationError(RobotSimError):
    """Raised when model or input validation fails."""

class IKDidNotConvergeError(RobotSimError):
    """Raised when IK stops without meeting tolerances."""
