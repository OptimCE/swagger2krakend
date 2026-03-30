# Swagger to KrakenD Config Generator

Convert Swagger/OpenAPI YAML files to KrakenD API gateway configuration.

## Features

- **Single file mode**: Process one Swagger file
- **Multi-file mode**: Process multiple Swagger files (comma-separated)
- **Service prefixing**: Each service's endpoints are prefixed with the filename (without extension)
- **Root exception**: Files named `root.yaml` get no prefix (endpoints remain at root path)
- **Extra-config**: External JSON configuration with environment variable substitution
- **File upload detection**: Special handling for multipart/form-data endpoints
- **CI-ready**: Fails fast if any swagger file is missing

## Usage

### Single File
```bash
python3 app.py swagger.yaml
python3 app.py swagger.yaml -o custom-output.json
```

### Multiple Files
```bash
python3 app.py users.yaml,orders.yaml
python3 app.py users.yaml,orders.yaml -o combined-config.json
```

### Extra Config

Use `extra-config.json` to define global endpoint configuration with environment variable substitution:

```bash
python3 app.py swagger.yaml -e extra-config.json
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
    ]
  }
}
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SWAGGER_FILE` | `swagger.yaml` | Input swagger file(s) |
| `EXTRA_CONFIG` | `extra-config.json` | Path to extra-config.json |
| `BACKEND_HOST` | `http://localhost:3000` | Backend host URL |
| `OUTPUT_FILE` | `krakend.json` | Output file path |
| `KEYCLOAK_URL` | - | Keycloak URL (required if using extra-config) |
| `REALM_NAME` | - | Keycloak realm name (required if using extra-config) |
| `ISSUER` | - | JWT issuer (required if using extra-config) |

### CLI Options

```bash
python3 app.py [-h] [-o OUTPUT] [-e EXTRA_CONFIG] [--backend-host BACKEND_HOST] [swagger_file]
```

### Root File Special Case

Files named `root.yaml` get no prefix:
```bash
python3 app.py root.yaml,users.yaml
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
- `1`: Error (missing swagger file, missing env var, etc.)
