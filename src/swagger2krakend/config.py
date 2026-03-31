"""Configuration utilities for loading and merging configs."""

import json
import os
import re


class MissingEnvVarError(Exception):
    """Raised when a required environment variable is not set."""

    pass


def load_extra_config(filepath):
    """Load extra configuration from a JSON file."""
    with open(filepath, "r") as file:
        return json.load(file)


def substitute_env_vars(obj):
    """Recursively substitute ${VAR} patterns with environment variable values."""
    if isinstance(obj, str):
        pattern = r"\$\{([^}]+)\}"
        matches = re.findall(pattern, obj)
        for match in matches:
            env_value = os.getenv(match)
            if env_value is None:
                raise MissingEnvVarError(f"Environment variable '{match}' is not set but is required in config")
            obj = obj.replace(f"${{{match}}}", env_value)
        return obj
    elif isinstance(obj, dict):
        return {key: substitute_env_vars(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [substitute_env_vars(item) for item in obj]
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
