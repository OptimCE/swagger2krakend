<p align="center">
  <img src="docs/logo.svg" alt="OptimCE swagger2krakend logo" width="160">
</p>

# swagger2krakend

[![Website](https://img.shields.io/badge/Website-optimce.be-2e7d32.svg)](https://www.optimce.be/en/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![en](https://img.shields.io/badge/lang-en-43a047.svg)](README.md)
[![fr](https://img.shields.io/badge/lang-fr-lightgrey.svg)](docs/README.fr.md)
[![de](https://img.shields.io/badge/lang-de-lightgrey.svg)](docs/README.de.md)
[![nl](https://img.shields.io/badge/lang-nl-lightgrey.svg)](docs/README.nl.md)

Convert Swagger/OpenAPI YAML files to KrakenD API gateway configuration using a declarative YAML builder configuration format.

## Features

- **Declarative YAML Configuration**: Configure your entire API gateway structure in a single `krakend-builder.yaml` file.
- **Multi-file mode**: Process multiple Swagger/OpenAPI files into a single unified KrakenD configuration.
- **Per-service Backends**: Each service specifies its own backend host and prefix.
- **Service prefixing**: Service endpoints are mapped under their respective names automatically, with customizable overrides.
- **Root exception**: Services named `root` (or with empty prefixes) get no prefix (endpoints remain at the root path).
- **Extra-config injection**: Inject global and per-service extra plugins configs (like rate-limiting or JWT validation).
- **Environment & Local Variable Substitution**: Powerful Jinja2 template variable injection `{{ VAR_NAME }}` from the environment or localized YAML variables.
- **File upload detection**: Special handling for `multipart/form-data` endpoints.
- **Transparent proxy mode**: Optional `no-op` encoding on every endpoint, forwarding backend status codes, bodies and headers verbatim.
- **Streaming timeouts**: Optional longer timeout applied only to upload and file-download endpoints.

## Usage

Create a `krakend-builder.yaml` configuration file to map your backend services and Open API specifications.

```bash
python3 app.py -c krakend-builder.yaml -o output/krakend.json
```

### Builder Configuration (krakend-builder.yaml)

```yaml
global:
  # Global configurations applied to all endpoints (e.g. Auth validators)
  extra_config: ./config/auth.json
  # Optional gateway settings applied to generated endpoint configs.
  timeout: 30s
  stream_timeout: 3600s   # only applied to upload / file-download endpoints
  passthrough: true       # no-op encoding everywhere -> transparent reverse proxy
  input_headers:
    - Authorization
    - Content-Type
  # Variables that will be substituted in the global extra_config
  variables:
    KEYCLOAK_URL: http://keycloak:8080/keycloak
    REALM_NAME: optimce-realm
    ISSUER: http://localhost:8087/keycloak/realms/optimce-realm

services:
  # The key 'crm-backend' is the service name (used as the default prefix: /crm-backend/...)
  crm-backend:
    swagger: ./docs/openapi/swagger.yaml
    host: "http://crm-backend:80"
    # Specific per-service configuration (e.g. Rate limits)
    extra_config: ./config/ratelimit.json
    variables:
      max_rate: 100

  # 'root' is a special key that maps directly to the root path (/) by default
  root:
    swagger: ./config/root.yaml
    host: "http://crm-backend:80"
    
  # You can override the prefix explicitly
  microservice:
    swagger: ./microservice/openapi.yaml
    host: "http://microservice:8080"
    prefix: "/custom_prefix"
    # Public services can opt out of global auth/validator injection.
    auth: false
```

`auth` defaults to `true`. Set `auth: false` for hand-written public
passthroughs such as health probes and documentation endpoints. Path parameters
are normalized positionally (`{p1}`, `{p2}`, ...) to avoid KrakenD router
conflicts when routes use different parameter names at the same segment.

The generator provides backward-compatible fallback values for timeout,
forwarded headers, logging, error handling, and CORS. Use `global.timeout` and
`global.input_headers` to override the timeout and request headers. Use the
global extra-config file to override CORS settings; non-auth global settings
are merged into the root KrakenD configuration and list values replace the
fallback lists.

`global.stream_timeout` sets a longer per-endpoint timeout so that long-lived
streams (SSE) and large exports are not cut off by the short global timeout. It
is applied by the *kind* of endpoint — uploads (`multipart/form-data`) and file
downloads — and never by the encoding, so enabling `passthrough` does not hand
the streaming timeout to the rest of the API. It defaults to unset, leaving
every endpoint on the global timeout.

`global.passthrough` (default `false`) emits the `no-op` encoding on every
endpoint, turning the gateway into a transparent reverse proxy. Under any other
encoding KrakenD replaces a non-2xx backend response with its own bodyless 500
and collapses `201`/`202` into `200`; `no-op` returns the backend's status, body
and headers verbatim, which matters when the backend already speaks a structured
error envelope the client needs to read. The trade-off is that `no-op` bypasses
the proxy pipe: aggregation, merging, response manipulation, concurrent backends
and backend-level `extra_config` no longer apply. Router-pipe features are
unaffected, so `auth/validator` (and therefore `auth: false`),
`qos/ratelimit/router` and `security/cors` keep working exactly as before.

### Extra Config (auth.json example)

You can reference external JSON configuration files to apply KrakenD plugins. Jinja2 template syntax `{{ VAR_NAME }}` is supported and will be substituted from your builder's `variables` block or the system environment variables:

```json
{
  "auth/validator": {
    "alg": "RS256",
    "jwk_url": "{{ KEYCLOAK_URL }}/realms/{{ REALM_NAME }}/protocol/openid-connect/certs",
    "disable_jwk_security": true,
    "issuer": "{{ ISSUER }}",
    "propagate_claims": [
      ["sub", "x-user-id"],
      ["groups", "x-user-groups"],
      ["orgs", "x-user-orgs"]
    ],
    "cache": true
  }
}
```

For example, a Med2Go builder can override the fallback CORS configuration
without changing the parser:

```json
{
  "security/cors": {
    "allow_origins": ["http://localhost:4200"],
    "allow_methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    "allow_headers": ["Authorization", "Content-Type", "Accept-Language", "X-Request-ID"],
    "expose_headers": ["Content-Disposition", "X-RateLimit-Limit", "X-RateLimit-Remaining", "X-Request-ID"],
    "allow_credentials": true,
    "max_age": "12h"
  }
}
```

The repository's Med2Go example is in `../krakend/global-extra.json` and is
referenced by `../krakend/krakend-builder.yaml`.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CONFIG_FILE` | `krakend-builder.yaml` | Input builder YAML file path |
| `OUTPUT_FILE` | `krakend.json` | Output generated KrakenD configuration file path |

*Note: You can also pass any environment variables expected by your `extra_config` files if you don't define them explicitly inside the YAML `variables` blocks.*

### CLI Options

```bash
python3 app.py [-h] [-c CONFIG] [-o OUTPUT]
```

## Requirements

### Python
- Python 3.9+
- PyYAML
- Jinja2

Install dependencies:
```bash
pip install -r requirements.txt
```

### Docker (for testing)
- Docker
- KrakenD image (for validation tests)

The test Dockerfile natively pulls the KrakenD binary for configuration validation.

## Code Quality

Format with black and lint with ruff:
```bash
black src/
ruff check src/
```

## Docker

### Production Build
```bash
docker build -t swagger2krakend .
docker run -v $(pwd)/config:/config swagger2krakend python3 app.py -c /config/krakend-builder.yaml -o /config/krakend.json
```

### Test Build
Build and run tests with KrakenD configuration JSON validation natively:
```bash
docker build -t swagger2krakend-test -f Dockerfile.test .
docker run --rm swagger2krakend-test
```

## Exit Codes

- `0`: Success
- `1`: Error (missing files, parsing errors, syntax errors, missing variables)

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for how to set
up a development environment, run the quality gates, and open a pull request. By
participating, you agree to abide by our
[Code of Conduct](CODE_OF_CONDUCT.md).

## Security

Please report security vulnerabilities responsibly — see our
[security policy](SECURITY.md). Please **do not** open public issues for
vulnerabilities.

## License

Licensed under the [Apache License 2.0](LICENSE).
