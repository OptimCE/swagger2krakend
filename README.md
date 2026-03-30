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

Use `extra-config.json` to define global endpoint configuration with environment variable substitution:

```bash
python3 app.py 'swagger.yaml:http://localhost:3000' -e extra-config.json
```

#### extra-config.json example
```json
{
  "auth/validator": {
    "alg": "RS256",
    "jwk_url": "${KEYCLOAK_URL}/realms/${REALM_NAME}/protocol/openid-connect/certs",
    "disable_jwk_security": true,
    "issuer": "${ISSUER}",
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

- Python 3.x
- PyYAML

Install dependencies:
```bash
pip install pyyaml
```

## Code Quality

Format with black and lint with flake8:
```bash
black app.py
flake8 app.py
```

## Exit Codes

- `0`: Success
- `1`: Error (missing swagger file, missing env var, missing host, etc.)
