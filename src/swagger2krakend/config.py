"""Configuration utilities for loading and merging configs."""

import json
import os

import yaml
from jinja2 import Environment, StrictUndefined, TemplateError


class MissingEnvVarError(Exception):
    """Raised when a required environment variable is not set."""

    pass


def load_extra_config(filepath):
    """Load extra configuration from a JSON file."""
    with open(filepath, "r") as file:
        return json.load(file)


def load_builder_config(filepath):
    """Load builder configuration from a YAML file."""
    with open(filepath, "r") as file:
        return yaml.safe_load(file)


def _render_template(template_str, env_vars):
    """Render a Jinja template string with environment variables."""
    env = Environment(undefined=StrictUndefined)
    try:
        template = env.from_string(template_str)
        return template.render(**env_vars)
    except TemplateError as e:
        # Extract variable name from Jinja error message
        var_name = str(e).split("'")[-2] if "'" in str(e) else str(e).split('"')[-2]
        raise MissingEnvVarError(f"Environment variable '{var_name}' is not set but is required in config")


def substitute_env_vars(obj, local_vars=None):
    """Recursively substitute environment variable references using Jinja templating.

    Supports Jinja syntax like {{ VAR_NAME }} for environment variable substitution.
    Environment variables serve as fallback when a variable is not defined or is empty
    in the local_vars (config) dict.
    """
    env_vars = dict(os.environ)
    if local_vars:
        for key, value in local_vars.items():
            if value:
                env_vars[key] = value

    if isinstance(obj, str):
        return _render_template(obj, env_vars)
    elif isinstance(obj, dict):
        return {key: substitute_env_vars(value, local_vars) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [substitute_env_vars(item, local_vars) for item in obj]
    return obj


def merge_configs(base, override):
    """Deep merge two configuration dicts. Override values take precedence."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_configs(result[key], value)
        else:
            result[key] = value
    return result
