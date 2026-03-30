import argparse
import json
import os
import sys
import yaml
from pathlib import Path
from jinja2 import Environment, StrictUndefined, UndefinedError

print("Starting Swagger to KrakenD config generator...")

DEFAULT_SWAGGER_FILE = "swagger.yaml"
DEFAULT_OUTPUT_FILE = "krakend.json"

SWAGGER_FILE = os.getenv("SWAGGER_FILE", DEFAULT_SWAGGER_FILE)
OUTPUT_FILE = os.getenv("OUTPUT_FILE", DEFAULT_OUTPUT_FILE)

JINJA_ENV = Environment(variable_start_string="${", variable_end_string="}", undefined=StrictUndefined)


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
        try:
            template = JINJA_ENV.from_string(obj)
            return template.render(**os.environ)
        except UndefinedError as e:
            raise MissingEnvVarError(str(e)) from e
    if isinstance(obj, dict):
        return {key: substitute_env_vars(value) for key, value in obj.items()}
    if isinstance(obj, list):
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


def parse_swagger_entry(entry):
    if ":" in entry and not entry.endswith(":"):
        filepath, potential_host = entry.split(":", 1)
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
            if method not in ("get", "post", "put", "delete", "patch", "options"):
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


def load_global_extra_config(extra_config_path):
    if not extra_config_path:
        return None

    print(f"Loading extra config from: {extra_config_path}")
    raw_config = load_extra_config(extra_config_path)
    return substitute_env_vars(raw_config)


def validate_swagger_entries(swagger_entries):
    missing_hosts = [filepath for filepath, host in swagger_entries if host is None]
    if missing_hosts:
        files = ", ".join(missing_hosts)
        raise ValueError(f"No host specified for: {files}. Use file:host syntax for all entries.")

    missing_files = [filepath for filepath, _ in swagger_entries if not os.path.isfile(filepath)]
    if missing_files:
        files = ", ".join(missing_files)
        raise FileNotFoundError(f"Swagger file(s) not found: {files}")


def build_combined_config(swagger_entries, global_extra_config):
    combined_config = None

    for filepath, api_host in swagger_entries:
        swagger_data = load_swagger(filepath)
        service_name = Path(filepath).stem
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
        raise ValueError("No valid swagger files found.")

    return combined_config


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
        default=None,
        help="Optional path to extra-config.json file for global endpoint configuration.",
    )
    args = parser.parse_args()

    if args.extra_config and not os.path.isfile(args.extra_config):
        parser.error(f"extra-config file not found: {args.extra_config}")

    return args


if __name__ == "__main__":
    args = parse_args()

    try:
        global_extra_config = load_global_extra_config(args.extra_config)
        swagger_entries = [f.strip() for f in args.swagger_file.split(",")]
        swagger_entries = [parse_swagger_entry(e) for e in swagger_entries]
        validate_swagger_entries(swagger_entries)
        combined_config = build_combined_config(swagger_entries, global_extra_config)

        with open(args.output, "w") as f:
            json.dump(combined_config, f, indent=4)

        print(f"Success! '{args.output}' has been generated.")
        print(f"Total endpoints configured: {len(combined_config['endpoints'])}")

    except MissingEnvVarError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except (ValueError, FileNotFoundError) as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)
