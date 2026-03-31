"""CLI interface for swagger2krakend."""

import argparse
import json
import os
import sys

from swagger2krakend.config import (
    MissingEnvVarError,
    load_extra_config,
    substitute_env_vars,
)
from swagger2krakend.parser import (
    generate_krakend_config,
    get_service_name,
    load_swagger,
    parse_swagger_entry,
)

DEFAULT_SWAGGER_FILE = "swagger.yaml"
DEFAULT_EXTRA_CONFIG = "extra-config.json"
DEFAULT_OUTPUT_FILE = "krakend.json"

SWAGGER_FILE = os.getenv("SWAGGER_FILE", DEFAULT_SWAGGER_FILE)
OUTPUT_FILE = os.getenv("OUTPUT_FILE", DEFAULT_OUTPUT_FILE)
EXTRA_CONFIG = os.getenv("EXTRA_CONFIG", DEFAULT_EXTRA_CONFIG)


def parse_args():
    """Parse command-line arguments."""
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


def main(args=None):
    """Main entry point for the CLI."""
    if args is None:
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
