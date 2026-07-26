"""CLI interface for swagger2krakend."""

import argparse
import json
import os
import sys

from swagger2krakend.config import (
    MissingEnvVarError,
    load_builder_config,
    load_extra_config,
    substitute_env_vars,
)
from swagger2krakend.parser import (
    generate_krakend_config,
    load_swagger,
)

DEFAULT_CONFIG_FILE = "krakend-builder.yaml"
DEFAULT_OUTPUT_FILE = "krakend.json"

CONFIG_FILE = os.getenv("CONFIG_FILE", DEFAULT_CONFIG_FILE)
OUTPUT_FILE = os.getenv("OUTPUT_FILE", DEFAULT_OUTPUT_FILE)


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Generate KrakenD config from a YAML builder config.")
    parser.add_argument(
        "-c",
        "--config",
        default=CONFIG_FILE,
        help="Path to krakend-builder.yaml configuration file.",
    )
    parser.add_argument("-o", "--output", default=OUTPUT_FILE, help="Output JSON file path.")
    return parser.parse_args()


def main(args=None):
    """Main entry point for the CLI."""
    if args is None:
        args = parse_args()

    try:
        if not os.path.isfile(args.config):
            print(f"Error: Configuration file not found: {args.config}")
            sys.exit(1)

        builder_config = load_builder_config(args.config)

        global_section = builder_config.get("global", {})
        global_extra_config_path = global_section.get("extra_config")
        global_vars = global_section.get("variables", {})
        global_input_headers = global_section.get("input_headers")
        global_timeout = global_section.get("timeout", "3000ms")
        # Optional gateway-wide overrides (default to the tool's historical behaviour).
        global_stream_timeout = global_section.get("stream_timeout")
        global_passthrough = global_section.get("passthrough", False)

        global_extra_config = None
        if global_extra_config_path and os.path.isfile(global_extra_config_path):
            print(f"Loading global extra config from: {global_extra_config_path}")
            raw_config = load_extra_config(global_extra_config_path)
            global_extra_config = substitute_env_vars(raw_config, global_vars)

        services = builder_config.get("services", {})
        if not services:
            print("Error: No services defined in the configuration file.")
            sys.exit(1)

        combined_config = None

        for service_key, service_options in services.items():
            swagger_filepath = service_options.get("swagger")
            api_host = service_options.get("host")

            if not swagger_filepath or not api_host:
                print(f"Error: Service '{service_key}' must specify 'swagger' and 'host'.")
                sys.exit(1)

            if not os.path.isfile(swagger_filepath):
                print(f"Error: Swagger file not found for service '{service_key}': {swagger_filepath}")
                sys.exit(1)

            service_vars = service_options.get("variables", {})
            service_extra_config_path = service_options.get("extra_config")

            service_extra_config = None
            if service_extra_config_path and os.path.isfile(service_extra_config_path):
                print(f"Loading service extra config from: {service_extra_config_path}")
                raw_config = load_extra_config(service_extra_config_path)
                service_extra_config = substitute_env_vars(raw_config, service_vars)

            service_prefix = service_options.get("prefix")
            if service_prefix is None:
                service_prefix = "" if service_key == "root" else f"/{service_key}"

            # auth: false marks the service public — the global auth/validator
            # is not injected into its endpoints (e.g. health probes, docs).
            service_auth = service_options.get("auth", True)

            swagger_data = load_swagger(swagger_filepath)

            service_config = generate_krakend_config(
                swagger_data,
                api_host=api_host,
                service_prefix=service_prefix,
                global_extra_config=global_extra_config,
                service_extra_config=service_extra_config,
                include_auth=service_auth,
                input_headers=global_input_headers,
                timeout=global_timeout,
                stream_timeout=global_stream_timeout,
                passthrough=global_passthrough,
            )

            if combined_config is None:
                combined_config = service_config
            else:
                combined_config["endpoints"].extend(service_config["endpoints"])

        if combined_config is None:
            print("Error: Could not generate configuration.")
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
