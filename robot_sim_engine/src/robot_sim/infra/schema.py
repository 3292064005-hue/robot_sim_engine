from __future__ import annotations

from copy import deepcopy

from robot_sim.model.solver_config import (
    SUPPORTED_TRAJECTORY_PLANNER_STAGES,
    SUPPORTED_TRAJECTORY_POSTPROCESSOR_STAGES,
    SUPPORTED_TRAJECTORY_RETIME_STAGES,
    SUPPORTED_TRAJECTORY_STAGE_KINDS,
    SUPPORTED_STAGE_PROVIDER_DEPLOYMENT_TIERS,
    SUPPORTED_STAGE_PROVIDER_STATUSES,
    SUPPORTED_TRAJECTORY_VALIDATE_STAGES,
    SUPPORTED_TRAJECTORY_VALIDATION_LAYERS,
)


class SchemaError(ValueError):
    pass


class ConfigSchema:
    @staticmethod
    def validate_app_config(config: dict) -> dict:
        validated = deepcopy(config)
        window = validated.setdefault("window", {})
        plots = validated.setdefault("plots", {})
        render = validated.setdefault("render", {})
        advice = render.setdefault("advice", {})
        ConfigSchema._require_positive_int(window, "width")
        ConfigSchema._require_positive_int(window, "height")
        ConfigSchema._require_positive_int(plots, "max_points")
        for key in ("splitter_sizes", "vertical_splitter_sizes"):
            if key in window:
                values = window[key]
                if not isinstance(values, list) or not values or any(int(v) <= 0 for v in values):
                    raise SchemaError(f"window.{key} must be a non-empty list of positive ints")
        for key in ("high_p95_ms", "high_average_ms", "high_failure_ratio", "high_span_rate_per_sec"):
            if key in advice and float(advice[key]) < 0.0:
                raise SchemaError(f"render.advice.{key} must be >= 0")
        return validated

    @staticmethod
    def validate_solver_config(config: dict) -> dict:
        validated = deepcopy(config)
        ik = validated.setdefault("ik", {})
        traj = validated.setdefault("trajectory", {})
        if str(ik.get("mode", "dls")) not in {"pinv", "dls", "lm", "analytic_6r"}:
            raise SchemaError("ik.mode must be 'pinv', 'dls', 'lm' or 'analytic_6r'")
        for key in ("max_iters", "retry_count", "random_seed"):
            if key in ik and int(ik[key]) < 0:
                raise SchemaError(f"ik.{key} must be >= 0")
        for key in (
            "pos_tol",
            "ori_tol",
            "damping_lambda",
            "step_scale",
            "joint_limit_weight",
            "manipulability_weight",
            "orientation_weight",
            "max_step_norm",
            "singularity_cond_threshold",
            "min_damping_lambda",
            "max_damping_lambda",
            "orientation_relaxation_pos_multiplier",
            "orientation_relaxation_ori_multiplier",
        ):
            if key in ik and float(ik[key]) < 0.0:
                raise SchemaError(f"ik.{key} must be >= 0")
        if "min_damping_lambda" in ik and "max_damping_lambda" in ik:
            if float(ik["min_damping_lambda"]) > float(ik["max_damping_lambda"]):
                raise SchemaError("ik.min_damping_lambda must be <= ik.max_damping_lambda")
        if "duration" in traj and float(traj["duration"]) <= 0.0:
            raise SchemaError("trajectory.duration must be > 0")
        if "dt" in traj and float(traj["dt"]) <= 0.0:
            raise SchemaError("trajectory.dt must be > 0")
        if "validation_layers" in traj:
            layers = traj["validation_layers"]
            if not isinstance(layers, (list, tuple)) or not layers:
                raise SchemaError("trajectory.validation_layers must be a non-empty list")
            normalized = []
            seen = set()
            for item in layers:
                token = str(item).strip()
                if not token:
                    raise SchemaError("trajectory.validation_layers entries must be non-empty strings")
                if token not in SUPPORTED_TRAJECTORY_VALIDATION_LAYERS:
                    raise SchemaError(
                        f"trajectory.validation_layers contains unsupported layer: {token}"
                    )
                if token in seen:
                    continue
                seen.add(token)
                normalized.append(token)
            traj["validation_layers"] = normalized
        if 'pipeline_id' in traj and not str(traj.get('pipeline_id', '')).strip():
            raise SchemaError('trajectory.pipeline_id must be a non-empty string')

        declared_stage_ids = {
            'planner': set(SUPPORTED_TRAJECTORY_PLANNER_STAGES),
            'retime': set(SUPPORTED_TRAJECTORY_RETIME_STAGES),
            'validate': set(SUPPORTED_TRAJECTORY_VALIDATE_STAGES),
            'postprocessor': set(SUPPORTED_TRAJECTORY_POSTPROCESSOR_STAGES),
        }
        if 'stage_catalog' in traj:
            catalog = traj['stage_catalog']
            if not isinstance(catalog, (list, tuple)):
                raise SchemaError('trajectory.stage_catalog must be a list')
            normalized_catalog = []
            for entry in catalog:
                if not isinstance(entry, dict):
                    raise SchemaError('trajectory.stage_catalog entries must be mapping objects')
                stage_id = str(entry.get('id', entry.get('stage_id', ''))).strip()
                stage_kind = str(entry.get('kind', '')).strip()
                factory = str(entry.get('factory', '')).strip()
                if not stage_id:
                    raise SchemaError('trajectory.stage_catalog[].id must be a non-empty string')
                if stage_kind not in SUPPORTED_TRAJECTORY_STAGE_KINDS:
                    raise SchemaError(f'trajectory.stage_catalog[].kind must be one of {SUPPORTED_TRAJECTORY_STAGE_KINDS!r}')
                if not factory:
                    raise SchemaError('trajectory.stage_catalog[].factory must be a non-empty string')
                declared_stage_ids[stage_kind].add(stage_id)
                aliases = entry.get('aliases', ()) or ()
                if not isinstance(aliases, (list, tuple)):
                    raise SchemaError('trajectory.stage_catalog[].aliases must be a list')
                status = str(entry.get('status', 'stable') or 'stable').strip()
                if status not in SUPPORTED_STAGE_PROVIDER_STATUSES:
                    raise SchemaError(
                        'trajectory.stage_catalog[].status must be one of '
                        f'{SUPPORTED_STAGE_PROVIDER_STATUSES!r}'
                    )
                deployment_tier = str(entry.get('deployment_tier', 'production') or 'production').strip()
                if deployment_tier not in SUPPORTED_STAGE_PROVIDER_DEPLOYMENT_TIERS:
                    raise SchemaError(
                        'trajectory.stage_catalog[].deployment_tier must be one of '
                        f'{SUPPORTED_STAGE_PROVIDER_DEPLOYMENT_TIERS!r}'
                    )
                enabled_profiles = entry.get('enabled_profiles', ()) or ()
                if not isinstance(enabled_profiles, (list, tuple)):
                    raise SchemaError('trajectory.stage_catalog[].enabled_profiles must be a list')
                required_caps = entry.get('required_host_capabilities', ()) or ()
                optional_caps = entry.get('optional_host_capabilities', ()) or ()
                if not isinstance(required_caps, (list, tuple)) or not isinstance(optional_caps, (list, tuple)):
                    raise SchemaError('trajectory.stage_catalog[] capability declarations must be lists')
                normalized_catalog.append(
                    {
                        'id': stage_id,
                        'provider_id': str(entry.get('provider_id', stage_id) or stage_id),
                        'kind': stage_kind,
                        'factory': factory,
                        'aliases': [str(alias).strip() for alias in aliases if str(alias).strip()],
                        'metadata': dict(entry.get('metadata', {}) or {}),
                        'enabled_profiles': [str(profile).strip() for profile in enabled_profiles if str(profile).strip()],
                        'status': status,
                        'deployment_tier': deployment_tier,
                        'required_host_capabilities': [str(item).strip() for item in required_caps if str(item).strip()],
                        'optional_host_capabilities': [str(item).strip() for item in optional_caps if str(item).strip()],
                        'fallback_stage_id': str(entry.get('fallback_stage_id', '') or '').strip(),
                        'replace': bool(entry.get('replace', False)),
                    }
                )
            traj['stage_catalog'] = normalized_catalog

        if 'pipelines' in traj:
            pipelines = traj['pipelines']
            if not isinstance(pipelines, (list, tuple)) or not pipelines:
                raise SchemaError('trajectory.pipelines must be a non-empty list')
            normalized_pipelines = []
            seen_pipeline_ids = set()
            for entry in pipelines:
                if not isinstance(entry, dict):
                    raise SchemaError('trajectory.pipelines entries must be mapping objects')
                pipeline_id = str(entry.get('id', entry.get('pipeline_id', ''))).strip()
                if not pipeline_id:
                    raise SchemaError('trajectory.pipelines[].id must be a non-empty string')
                if pipeline_id in seen_pipeline_ids:
                    raise SchemaError(f'duplicate trajectory pipeline id: {pipeline_id}')
                seen_pipeline_ids.add(pipeline_id)
                planner_stage = str(entry.get('planner_stage', entry.get('planner_stage_id', 'default_planner'))).strip()
                retime_stage = str(entry.get('retime_stage', entry.get('retime_stage_id', 'builtin_scaling'))).strip()
                validate_stage = str(entry.get('validate_stage', entry.get('validate_stage_id', 'validate_trajectory'))).strip()
                if planner_stage not in declared_stage_ids['planner']:
                    raise SchemaError(f'unsupported trajectory planner stage: {planner_stage}')
                if retime_stage not in declared_stage_ids['retime']:
                    raise SchemaError(f'unsupported trajectory retime stage: {retime_stage}')
                if validate_stage not in declared_stage_ids['validate']:
                    raise SchemaError(f'unsupported trajectory validate stage: {validate_stage}')
                postprocessors = entry.get('postprocessors', entry.get('postprocessor_stage_ids', ())) or ()
                if not isinstance(postprocessors, (list, tuple)):
                    raise SchemaError('trajectory.pipelines[].postprocessors must be a list')
                normalized_post = []
                for stage in postprocessors:
                    stage_id = str(stage).strip()
                    if not stage_id:
                        raise SchemaError('trajectory.pipelines[].postprocessors entries must be non-empty strings')
                    if stage_id not in declared_stage_ids['postprocessor']:
                        raise SchemaError(f'unsupported trajectory postprocessor stage: {stage_id}')
                    normalized_post.append(stage_id)
                aliases = entry.get('aliases', ()) or ()
                if not isinstance(aliases, (list, tuple)):
                    raise SchemaError('trajectory.pipelines[].aliases must be a list')
                normalized_pipelines.append(
                    {
                        'id': pipeline_id,
                        'planner_stage': planner_stage,
                        'retime_stage': retime_stage,
                        'validate_stage': validate_stage,
                        'postprocessors': normalized_post,
                        'aliases': [str(alias).strip() for alias in aliases if str(alias).strip()],
                        'metadata': dict(entry.get('metadata', {}) or {}),
                    }
                )
            traj['pipelines'] = normalized_pipelines
        return validated

    @staticmethod
    def _require_positive_int(section: dict, key: str) -> None:
        if key not in section:
            return
        if int(section[key]) <= 0:
            raise SchemaError(f"{key} must be > 0")
