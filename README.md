# Swagger to KrakenD Config Generator

This tool converts Swagger/OpenAPI YAML files to KrakenD API gateway configuration.

## Features

- **Single file mode**: Process one Swagger file (backward compatible)
- **Multi-file mode**: Process multiple Swagger files (comma-separated)
- **Service prefixing**: Each service's endpoints are prefixed with the filename (without extension)
- **Root exception**: Files named `root.yaml` get no prefix (endpoints remain at root path)
- **Keycloak integration**: Automatic authentication configuration for all endpoints
- **File upload detection**: Special handling for multipart/form-data endpoints

## Usage

### Single File (Original Behavior)
```bash
python app.py swagger.yaml
python app.py swagger.yaml -o custom-output.json
```

### Multiple Files (New Feature)
```bash
python app.py users.yaml,orders.yaml,payments.yaml
python app.py users.yaml,orders.yaml -o combined-config.json
```

### Root File Special Case
If you have a file named `root.yaml`, its endpoints will NOT be prefixed:
```bash
python app.py root.yaml,users.yaml
# root.yaml endpoints: /health, /version
# users.yaml endpoints: /users/users, /users/{id}, etc.
```

## Output

The tool generates a KrakenD configuration file (`krakend.json` by default) with:
- Basic KrakenD configuration (version 3, port 8080)
- Telemetry and CORS settings
- Keycloak authentication for all endpoints
- All endpoints from all processed services

## Example

Given these files:
- `users.yaml` with endpoints: `/users`, `/users/{id}`
- `orders.yaml` with endpoints: `/orders`, `/orders/{id}`
- `root.yaml` with endpoints: `/health`, `/version`

Running: `python app.py root.yaml,users.yaml,orders.yaml`

Would produce endpoints:
- `/health` (from root.yaml)
- `/version` (from root.yaml)
- `/users/users` (from users.yaml)
- `/users/users/{id}` (from users.yaml)
- `/orders/orders` (from orders.yaml)
- `/orders/orders/{id}` (from orders.yaml)

## Requirements

- Python 3.x
- PyYAML (`pip install pyyaml`)