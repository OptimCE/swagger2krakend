"""Swagger/OpenAPI parser and KrakenD config generator."""

from copy import deepcopy
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


JSON_MEDIA_TYPES = {"application/json", "application/problem+json"}

# Default headers forwarded to backends when the builder config does not set
# global.input_headers. Note that headers injected by auth/validator's
# propagate_claims are stripped unless declared here — the input_headers filter
# applies to the final header set.
DEFAULT_INPUT_HEADERS = [
    "x-user-id",
    "x-community-id",
    "x-user-groups",
    "x-user-orgs",
    "Content-Length",
    "Content-Type",
    "Accept-Language",
]

# Backward-compatible fallback for callers that do not provide a global
# extra_config. Applications should override security/cors through the builder
# configuration when they need non-default origins or headers.
DEFAULT_EXTRA_CONFIG = {
    "router": {
        "return_error_msg": True,
    },
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
            "Accept-Language",
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
            "Accept-Language",
            "Content-Disposition",
        ],
    },
}


def _normalize_path_params(path):
    """Rename whole-segment path params positionally ({p1}, {p2}, ...).

    KrakenD's router (gin) panics when two routes use DIFFERENT param names at
    the same segment position — e.g. /prices/{medicine_id} vs
    /prices/{medicine_price_id}/price. Param names are internal to KrakenD:
    the captured value is substituted into the identical url_pattern either
    way, so positional renaming is transparent to the backend. Segments that
    are not a bare {param} (e.g. {token}.ics) are left untouched.
    """
    segments = path.split("/")
    count = 0
    normalized = []
    for segment in segments:
        if segment.startswith("{") and segment.endswith("}"):
            count += 1
            normalized.append(f"{{p{count}}}")
        else:
            normalized.append(segment)
    return "/".join(normalized)


def _resolve_response(response, swagger):
    """Resolve a response object, following a local $ref into components.responses."""
    ref = response.get("$ref")
    if ref and ref.startswith("#/components/responses/"):
        name = ref.rsplit("/", 1)[-1]
        return swagger.get("components", {}).get("responses", {}).get(name, {})
    return response


def _is_file_response(details, swagger):
    """Return True when an operation's success (2xx) response is a file/binary download.

    Detected by a content media type other than JSON, or a schema with format: binary.
    Such endpoints must use KrakenD's 'no-op' encoding so the gateway streams the body
    instead of trying to JSON-parse it.
    """
    for status, response in details.get("responses", {}).items():
        if not str(status).startswith("2"):
            continue
        content = _resolve_response(response, swagger).get("content", {})
        for media_type, media_obj in content.items():
            if media_type not in JSON_MEDIA_TYPES:
                return True
            schema = (media_obj or {}).get("schema", {})
            if isinstance(schema, dict) and schema.get("format") == "binary":
                return True
    return False


def generate_krakend_config(
    swagger,
    api_host,
    service_prefix="",
    global_extra_config=None,
    service_extra_config=None,
    include_auth=True,
    input_headers=None,
    timeout="3000ms",
    stream_timeout=None,
    passthrough=False,
):
    """Generate a KrakenD configuration dict from a Swagger spec.

    include_auth=False skips the global auth/validator injection for this
    service (public, unauthenticated endpoints). input_headers overrides
    DEFAULT_INPUT_HEADERS; timeout sets the service-level gateway timeout.
    passthrough=True forces the 'no-op' encoding on every endpoint, turning the
    gateway into a transparent reverse proxy; stream_timeout overrides the
    timeout on streaming/download endpoints only.
    """
    if input_headers is None:
        input_headers = DEFAULT_INPUT_HEADERS

    krakend_config = {
        "$schema": "https://www.krakend.io/schema/v2.13/krakend.json",
        "version": 3,
        "name": swagger.get("info", {}).get("title", "API Gateway"),
        "port": 8080,
        "timeout": timeout,
        "cache_ttl": "0s",
        # Forward the raw error body of a single backend to the client (paired with
        # each backend's backend/http.return_error_code). Without this, KrakenD
        # obfuscates non-2xx responses and strips the body, so structured error
        # codes (e.g. member 50013 "member_has_active_meters") never reach the SPA.
        "extra_config": deepcopy(DEFAULT_EXTRA_CONFIG),
        "endpoints": [],
    }

    endpoint_extra_config = None
    if global_extra_config:
        # auth/validator is gated per-service (include_auth) so public services
        # stay unauthenticated; non-auth globals (e.g. security/cors) always
        # merge into the root extra_config.
        if include_auth:
            endpoint_extra_config = {k: v for k, v in global_extra_config.items() if k == "auth/validator"}
        non_auth_config = {k: v for k, v in global_extra_config.items() if k != "auth/validator"}
        if non_auth_config:
            krakend_config["extra_config"] = merge_configs(krakend_config["extra_config"], non_auth_config)

    paths = swagger.get("paths", {})

    for path, methods in paths.items():
        for method, details in methods.items():
            if method not in ["get", "post", "put", "delete", "patch", "options"]:
                continue

            is_upload = "multipart/form-data" in details.get("consumes", []) or "multipart/form-data" in details.get(
                "requestBody", {}
            ).get("content", {})
            is_download = _is_file_response(details, swagger)
            # Streaming/download endpoints ALWAYS need no-op so the gateway pipes the body
            # through; with `passthrough` every other endpoint does too. Tracked separately
            # from `encoding` because `stream_timeout` keys off the KIND of endpoint, not off
            # the encoding — otherwise enabling `passthrough` would silently hand the long
            # streaming timeout to every endpoint.
            is_stream = is_upload or is_download
            encoding = "no-op" if (passthrough or is_stream) else "json"

            normalized_path = _normalize_path_params(path)
            endpoint = {
                "endpoint": f"{service_prefix}{normalized_path}",
                "input_headers": input_headers,
                "input_query_strings": ["*"],
                "method": method.upper(),
                "output_encoding": encoding,
                "backend": [
                    {
                        "url_pattern": normalized_path,
                        "host": [api_host],
                        "encoding": encoding,
                        # Return the backend's real HTTP status code instead of an
                        # obfuscated 500. Paired with the global router.return_error_msg,
                        # this forwards the backend error body verbatim so the SPA can
                        # read error_code. Ignored on no-op encodings (already stream the body).
                        "extra_config": {"backend/http": {"return_error_code": True}},
                    }
                ],
            }

            # Streaming / download endpoints (SSE, file exports) must not be killed by the
            # short global timeout — give them a longer per-endpoint one when asked.
            if is_stream and stream_timeout:
                endpoint["timeout"] = stream_timeout

            if endpoint_extra_config or service_extra_config:
                combined_endpoint_config = (endpoint_extra_config or {}).copy()
                if service_extra_config:
                    combined_endpoint_config = merge_configs(combined_endpoint_config, service_extra_config)
                if combined_endpoint_config:
                    endpoint["extra_config"] = combined_endpoint_config

            krakend_config["endpoints"].append(endpoint)

    return krakend_config
