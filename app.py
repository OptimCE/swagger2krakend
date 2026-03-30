import argparse
import json
import os
import re
import sys
import yaml
from pathlib import Path

print("Starting Swagger to KrakenD config generator...")

DEFAULT_SWAGGER_FILE = "swagger.yaml"
DEFAULT_EXTRA_CONFIG = "extra-config.json"
DEFAULT_OUTPUT_FILE = "krakend.json"

SWAGGER_FILE = os.getenv("SWAGGER_FILE", DEFAULT_SWAGGER_FILE)
OUTPUT_FILE = os.getenv("OUTPUT_FILE", DEFAULT_OUTPUT_FILE)
EXTRA_CONFIG = os.getenv("EXTRA_CONFIG", DEFAULT_EXTRA_CONFIG)


class MissingEnvVarError(Exception):
    pass


def load_swagger(filepath):
    with open(filepath, "r") as file:
        return yaml.safe_load(file)


def load_extra_config(filepath):
    with open(filepath, "r") as file:
        return json.load(file)


def substitute_env_vars(obj):
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
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_configs(result[key], value)
        else:
            result[key] = value
    return result


def get_service_name(filepath):
    return Path(filepath).stem


def parse_swagger_entry(entry):
    if ":" in entry and not entry.endswith(":"):
        parts = entry.split(":", 1)
        filepath, potential_host = parts[0], parts[1]
        if "://" in potential_host or potential_host.startswith("http"):
            return filepath, potential_host
        return entry, None
    return entry, None


def generate_krakend_config(swagger, api_host, service_prefix="", global_extra_config=None):
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
                "method": method.upper(),
                "output_encoding": encoding,
                "backend": [{"url_pattern": path, "host": [api_host], "encoding": encoding}],
            }

            if endpoint_extra_config:
                endpoint["extra_config"] = endpoint_extra_config.copy()

            krakend_config["endpoints"].append(endpoint)

    return krakend_config


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate KrakenD config from Swagger/OpenAPI YAML files. "
        "Supports single or multiple files (comma-separated)."
    )
    parser.add_argument(
        "swagger_file",
        nargs="?",
        default=SWAGGER_FILE,
        help="Path to Swagger YAML file(s). Use comma-separated for multiple files. "
        "Service name derived from filename (without extension).",
    )
    parser.add_argument("-o", "--output", default=OUTPUT_FILE, help="Output JSON file path.")
    parser.add_argument(
        "-e",
        "--extra-config",
        default=EXTRA_CONFIG,
        help="Path to extra-config.json file for global endpoint configuration.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    try:
        global_extra_config = None
        if os.path.isfile(args.extra_config):
            print(f"Loading extra config from: {args.extra_config}")
            raw_config = load_extra_config(args.extra_config)
            global_extra_config = substitute_env_vars(raw_config)

        swagger_entries = [f.strip() for f in args.swagger_file.split(",")]
        swagger_entries = [parse_swagger_entry(e) for e in swagger_entries]

        missing_hosts = [f for f, h in swagger_entries if h is None]
        if missing_hosts:
            for f in missing_hosts:
                print(f"Error: No host specified for {f}")
            print("Error: All swagger files must specify a host (file:host syntax).")
            sys.exit(1)

        missing_files = [f for f, _ in swagger_entries if not os.path.isfile(f)]
        if missing_files:
            for f in missing_files:
                print(f"Error: Could not find {f}")
            print("Error: One or more swagger files not found.")
            sys.exit(1)

        combined_config = None

        for filepath, api_host in swagger_entries:
            swagger_data = load_swagger(filepath)
            service_name = get_service_name(filepath)
            service_prefix = "" if service_name == "root" else f"/{service_name}"

            service_config = generate_krakend_config(
                swagger_data,
                api_host=api_host,
                service_prefix=service_prefix,
                global_extra_config=global_extra_config,
            )

            if combined_config is None:
                combined_config = service_config
            else:
                combined_config["endpoints"].extend(service_config["endpoints"])

        if combined_config is None:
            print("Error: No valid swagger files found.")
            sys.exit(1)

        with open(args.output, "w") as f:
            json.dump(combined_config, f, indent=4)

        print(f"Success! '{args.output}' has been generated.")
        print(f"Total endpoints configured: {len(combined_config['endpoints'])}")

    except MissingEnvVarError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)
