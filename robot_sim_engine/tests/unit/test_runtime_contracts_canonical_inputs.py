from __future__ import annotations

import pytest

from robot_sim.domain.runtime_contracts import render_capability_matrix_markdown, render_module_status_markdown


def test_render_module_status_markdown_ignores_unknown_detail_fields() -> None:
    markdown = render_module_status_markdown({
        'module.a': {
            'status': 'stable',
            'enabled': True,
            'unexpected_field': 'ignored',
            'notes': ('ok',),
        }
    })
    assert 'unexpected_field' not in markdown


def test_render_capability_matrix_markdown_rejects_non_mapping_payload() -> None:
    with pytest.raises(TypeError):
        render_capability_matrix_markdown(())
