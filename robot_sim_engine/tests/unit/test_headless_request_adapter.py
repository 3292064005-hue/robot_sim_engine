from __future__ import annotations

import json

import pytest

from robot_sim.app.headless_api import HeadlessRequestError
from robot_sim.app.headless_request_adapter import HeadlessRequestContractAdapter


@pytest.fixture()
def adapter() -> HeadlessRequestContractAdapter:
    return HeadlessRequestContractAdapter(HeadlessRequestError)


def test_adapter_rejects_mutually_exclusive_sources(adapter: HeadlessRequestContractAdapter, tmp_path) -> None:
    request_path = tmp_path / 'req.json'
    request_path.write_text('{}', encoding='utf-8')
    with pytest.raises(HeadlessRequestError, match='mutually exclusive'):
        adapter.load(request_file=request_path, request_json='{}')


def test_adapter_rejects_invalid_inline_json(adapter: HeadlessRequestContractAdapter) -> None:
    with pytest.raises(HeadlessRequestError, match='invalid request_json'):
        adapter.load(request_json='{bad json}')


def test_adapter_rejects_missing_request_file(adapter: HeadlessRequestContractAdapter, tmp_path) -> None:
    with pytest.raises(HeadlessRequestError, match='request file not found'):
        adapter.load(request_file=tmp_path / 'missing.yaml')


def test_adapter_rejects_non_mapping_json_payload(adapter: HeadlessRequestContractAdapter) -> None:
    with pytest.raises(HeadlessRequestError, match='mapping object'):
        adapter.load(request_json=json.dumps([1, 2, 3]))


def test_adapter_loads_yaml_mapping(adapter: HeadlessRequestContractAdapter, tmp_path) -> None:
    request_path = tmp_path / 'req.yaml'
    request_path.write_text('robot: planar_2dof\nq: [0, 0]\n', encoding='utf-8')
    payload = adapter.load(request_file=request_path)
    assert payload == {'robot': 'planar_2dof', 'q': [0, 0]}


def test_adapter_rejects_non_mapping_yaml_payload_even_when_falsy(adapter: HeadlessRequestContractAdapter, tmp_path) -> None:
    request_path = tmp_path / 'request.yaml'
    request_path.write_text('[]\n', encoding='utf-8')

    with pytest.raises(HeadlessRequestError, match='request payload must be a mapping object'):
        adapter.load(request_file=request_path)
