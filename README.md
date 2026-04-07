# Swagger to KrakenD Config Generator

Convert Swagger/OpenAPI YAML files to KrakenD API gateway configuration.

## Features

- **Single file mode**: Process one Swagger file with its backend host
- **Multi-file mode**: Process multiple Swagger files (comma-separated)
- **Per-file backend**: Each swagger file specifies its own backend host
- **Service prefixing**: Each service's endpoints are prefixed with the filename (without extension)
- **Root exception**: Files named `root.yaml` get no prefix (endpoints remain at root path)
- **Extra-config**: External JSON configuration with environment variable substitution
- **File upload detection**: Special handling for multipart/form-data endpoints
- **CI-ready**: Fails fast if any swagger file is missing or lacks a host

## Usage

### Syntax: `filepath:host`

Each swagger file must specify its backend host using `filepath:host` syntax:

```bash
python3 app.py 'swagger.yaml:http://localhost:3000'
python3 app.py 'users.yaml:http://localhost:3001,orders.yaml:http://localhost:3002'
```

**Note:** The URL must include the port number (e.g., `:8080`, `:3000`).

### Single File
```bash
python3 app.py 'swagger.yaml:http://localhost:3000' -o custom-output.json
```

### Multiple Files
```bash
python3 app.py 'users.yaml:http://localhost:3001,orders.yaml:http://localhost:3002' -o combined-config.json
```

### Extra Config

Use `extra-config.json` to define global endpoint configuration with environment variable substitution using Jinja2 template syntax:

```bash
python3 app.py 'swagger.yaml:http://localhost:3000' -e extra-config.json
```

**Note:** Environment variables use Jinja2 syntax: `{{ VAR_NAME }}` instead of the old `${VAR_NAME}` syntax.

#### extra-config.json example
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

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SWAGGER_FILE` | `swagger.yaml` | Input swagger file(s) with hosts (`file:host` syntax) |
| `EXTRA_CONFIG` | `extra-config.json` | Path to extra-config.json |
| `OUTPUT_FILE` | `krakend.json` | Output file path |

### CLI Options

```bash
python3 app.py [-h] [-o OUTPUT] [-e EXTRA_CONFIG] swagger_file [...]
```

### Root File Special Case

Files named `root.yaml` get no prefix:

```bash
python3 app.py 'root.yaml:http://localhost:3000,users.yaml:http://localhost:3001'
# root.yaml endpoints: /health, /version
# users.yaml endpoints: /users/users, /users/{id}
```

## Requirements

### Python
- Python 3.x
- PyYAML
- Jinja2

Install dependencies:
```bash
pip install pyyaml jinja2
```

### Docker (for testing)
- Docker
- KrakenD image (for validation tests)

The test Dockerfile uses `krakend:2.13.3` for configuration validation.

## Code Quality

Format with black and lint with flake8:
```bash
black app.py
flake8 app.py
```

## Docker

### Production Build
```bash
docker build -t swagger2krakend .
docker run -v $(pwd)/input:/input -v $(pwd)/output:/output swagger2krakend 'input/swagger.yaml:http://localhost:3000' -o output/krakend.json
```

### Test Build
Build and run tests with KrakenD validation:
```bash
docker build -t swagger2krakend-test -f Dockerfile.test .
docker run swagger2krakend-test
```

## Exit Codes

- `0`: Success
- `1`: Error (missing swagger file, missing env var, missing host, etc.)
