from __future__ import annotations

from robot_sim.plugin_sdk import plugin_payload


class MinimalExamplePlanner:
    """Tiny planner plugin used as a public SDK reference."""

    def plan(self, req):
        return {
            'waypoint_count': len(getattr(req, 'waypoints', ()) or ()),
            'dt': float(getattr(req, 'dt', 0.02) or 0.02),
        }


def build_plugin(*, display_name: str = 'Example Cartesian planner'):
    return plugin_payload(
        MinimalExamplePlanner(),
        aliases=('example_planner_alias',),
        metadata={
            'family': 'cartesian',
            'display_name': display_name,
            'source': 'sdk_example',
        },
    )
