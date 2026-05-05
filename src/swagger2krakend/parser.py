"""Swagger/OpenAPI parser and KrakenD config generator."""

from pathlib import Path

import yaml

from swagger2krakend.config import merge_configs


def load_swagger(filepath):
    """Load a Swagger/OpenAPI YAML file."""
    with open(filepath, "r") as file:
        return yaml.safe_load(file)


def parse_swagger_entry(entry):
    """Parse a swagger entry that may contain a host specification.

    Format: 'path/to/file.yaml:host' or just 'path/to/file.yaml'

    Returns:
        tuple: (filepath, host_or_none)
    """
    if ":" in entry and not entry.endswith(":"):
        parts = entry.split(":", 1)
        filepath, potential_host = parts[0], parts[1]
        return filepath, potential_host
    return entry, None


def get_service_name(filepath):
    """Extract service name from filename (without extension)."""
    return Path(filepath).stem


def generate_krakend_config(swagger, api_host, service_prefix="", global_extra_config=None, service_extra_config=None):
    """Generate a KrakenD configuration dict from a Swagger spec."""
    krakend_config = {
        "$schema": "https://www.krakend.io/schema/v2.13/krakend.json",
        "version": 3,
        "name": swagger.get("info", {}).get("title", "API Gateway"),
        "port": 8080,
        "timeout": "3000ms",
        "cache_ttl": "0s",
        "extra_config": {
            "telemetry/logging": {
                "level": "INFO",
                "prefix": "[KRAKEND]",
                "stdout": True,
            },
            "security/cors": {
                "allow_origins": ["*"],
                "allow_methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
                "allow_headers": [
                    "Authorization",
                    "Content-Type",
                    "x-community-id",
                    "x-user-id",
                    "x-user-groups",
                    "x-user-orgs",
                ],
                "expose_headers": [
                    "x-user-id",
                    "x-user-groups",
                    "x-user-orgs",
                    "x-community-id",
                ],
            },
        },
        "endpoints": [],
    }

    endpoint_extra_config = None
    if global_extra_config:
        endpoint_extra_config = {k: v for k, v in global_extra_config.items() if k == "auth/validator"}
        non_auth_config = {k: v for k, v in global_extra_config.items() if k != "auth/validator"}
        if non_auth_config:
            krakend_config["extra_config"] = merge_configs(krakend_config["extra_config"], non_auth_config)

    paths = swagger.get("paths", {})

    for path, methods in paths.items():
        for method, details in methods.items():
            if method not in ["get", "post", "put", "delete", "patch", "options"]:
                continue

            is_upload = "multipart/form-data" in details.get("consumes", [])
            encoding = "no-op" if is_upload else "json"

            endpoint = {
                "endpoint": f"{service_prefix}{path}",
                "input_headers": [
                    "x-user-id",
                    "x-community-id",
                    "x-user-groups",
                    "x-user-orgs",
                    "Content-Length",
                    "Content-Type",
                ],
                "input_query_strings": ["*"],
                "method": method.upper(),
                "output_encoding": encoding,
                "backend": [{"url_pattern": path, "host": [api_host], "encoding": encoding}],
            }

            if endpoint_extra_config or service_extra_config:
                combined_endpoint_config = (endpoint_extra_config or {}).copy()
                if service_extra_config:
                    combined_endpoint_config = merge_configs(combined_endpoint_config, service_extra_config)
                if combined_endpoint_config:
                    endpoint["extra_config"] = combined_endpoint_config

            krakend_config["endpoints"].append(endpoint)

    return krakend_config
