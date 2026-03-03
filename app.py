import argparse
import json
import os
import yaml

print("Starting Swagger to KrakenD config generator...")
DEFAULT_SWAGGER_FILE = 'swagger.yaml'
DEFAULT_KEYCLOAK_URL = 'http://keycloak:8080'
DEFAULT_REALM_NAME = 'optimce-realm'
DEFAULT_BACKEND_HOST = 'http://localhost:3000'
DEFAULT_ISSUER = f'http://localhost:8081/realms/{DEFAULT_REALM_NAME}'
DEFAULT_OUTPUT_FILE = 'krakend.json'

# Fetch from environment variables with defaults
SWAGGER_FILE = os.getenv('SWAGGER_FILE', DEFAULT_SWAGGER_FILE)
OUTPUT_FILE = os.getenv('OUTPUT_FILE', DEFAULT_OUTPUT_FILE)
#keycloak
KEYCLOAK_URL = os.getenv('KEYCLOAK_URL', DEFAULT_KEYCLOAK_URL)
REALM_NAME = os.getenv('REALM_NAME', DEFAULT_REALM_NAME)
ISSUER = os.getenv('ISSUER', DEFAULT_ISSUER)
#crm-backend
BACKEND_HOST = os.getenv('BACKEND_HOST', DEFAULT_BACKEND_HOST)

def load_swagger(filepath):
    with open(filepath, 'r') as file:
        return yaml.safe_load(file)

def generate_krakend_config(swagger, keycloak_url, realm_name, backend_host, issuer):
    krakend_config = {
        "$schema": "https://www.krakend.io/schema/v2.6/krakend.json",
        "version": 3,
        "name": swagger.get('info', {}).get('title', 'API Gateway'),
        "port": 8080,
        "timeout": "3000ms",
        "cache_ttl": "0s",
        "extra_config": {
            "telemetry/logging": {
                "level": "INFO",
                "prefix": "[KRAKEND]",
                "stdout": True
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
                    "x-user-orgs"
                ],
                "expose_headers": [
                    "x-user-id",
                    "x-user-groups",
                    "x-user-orgs",
                    "x-community-id"
                ]
            }
        },
        "endpoints": []
    }

    paths = swagger.get('paths', {})
    
    for path, methods in paths.items():
        for method, details in methods.items():
            if method not in ['get', 'post', 'put', 'delete', 'patch', 'options']:
                continue

            # 1. Detect if this is a file upload route
            is_upload = 'multipart/form-data' in details.get('consumes', [])
            encoding = "no-op" if is_upload else "json"

            # 2. Build the endpoint object
            endpoint = {
                "endpoint": path,
                "input_headers": ["x-user-id","x-community-id","x-user-groups", "x-user-orgs", "Content-Length", "Content-Type"],
                "method": method.upper(),
                "output_encoding": encoding,
                "backend": [{
                    "url_pattern": path,
                    "host": [backend_host],
                    "encoding": encoding
                }]
            }
            headers_to_pass = ["Content-Length", "Content-Type"]
            # 3. Add Headers to pass (for uploads)
            #if is_upload:
            #    headers_to_pass.append()

            endpoint["headers_to_pass"] = headers_to_pass

            # 4. Add Keycloak Auth Validator
            # We add this to ALL routes found in swagger. 
            # If you have public routes, you might want to filter them here.
            endpoint["extra_config"] = {
                "auth/validator": {
                    "alg": "RS256",
                    "jwk_url": f"{keycloak_url}/realms/{realm_name}/protocol/openid-connect/certs",
                    "disable_jwk_security": True, # True because internal docker network often uses HTTP
                    "issuer": issuer,
                    "propagate_claims": [
                        ["sub", "x-user-id"],
                        ["groups","x-user-groups"],
                        ["orgs", "x-user-orgs"]
                    ]
                }
            }

            krakend_config['endpoints'].append(endpoint)

    return krakend_config

def parse_args():
    parser = argparse.ArgumentParser(description="Generate KrakenD config from a Swagger/OpenAPI YAML file.")
    parser.add_argument("swagger_file", nargs="?", default=SWAGGER_FILE, help="Path to the Swagger YAML file.")
    parser.add_argument("-o", "--output", default=OUTPUT_FILE, help="Output JSON file path.")
    parser.add_argument("--keycloak-url", default=KEYCLOAK_URL)
    parser.add_argument("--realm-name", default=REALM_NAME)
    parser.add_argument("--backend-host", default=BACKEND_HOST)
    parser.add_argument("--issuer", default=ISSUER)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    try:
        swagger_data = load_swagger(args.swagger_file)
        config = generate_krakend_config(
            swagger_data,
            keycloak_url=args.keycloak_url,
            realm_name=args.realm_name,
            backend_host=args.backend_host,
            issuer=args.issuer,
        )

        with open(args.output, 'w') as f:
            json.dump(config, f, indent=4)

        print(f"Success! '{args.output}' has been generated.")
        print(f"Total endpoints configured: {len(config['endpoints'])}")

    except FileNotFoundError:
        print(f"Error: Could not find {args.swagger_file}")
    except Exception as e:
        print(f"An error occurred: {e}")