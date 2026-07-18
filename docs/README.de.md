<p align="center">
  <img src="logo.svg" alt="swagger2krakend OptimCE-Logo" width="160">
</p>

# swagger2krakend

[![Website](https://img.shields.io/badge/Website-optimce.be-2e7d32.svg)](https://www.optimce.be/de/)
[![Lizenz](https://img.shields.io/badge/Lizenz-Apache%202.0-blue.svg)](../LICENSE)
[![en](https://img.shields.io/badge/lang-en-lightgrey.svg)](../README.md)
[![fr](https://img.shields.io/badge/lang-fr-lightgrey.svg)](README.fr.md)
[![de](https://img.shields.io/badge/lang-de-43a047.svg)](README.de.md)
[![nl](https://img.shields.io/badge/lang-nl-lightgrey.svg)](README.nl.md)

Konvertieren Sie Swagger/OpenAPI-YAML-Dateien mit einem deklarativen YAML-Builder-Konfigurationsformat in eine KrakenD-API-Gateway-Konfiguration.

## Funktionen

- **Deklarative YAML-Konfiguration**: Konfigurieren Sie die gesamte Struktur Ihres API-Gateways in einer einzigen `krakend-builder.yaml`-Datei.
- **Multi-Datei-Modus**: Verarbeiten Sie mehrere Swagger/OpenAPI-Dateien zu einer einzigen, vereinheitlichten KrakenD-Konfiguration.
- **Backends pro Service**: Jeder Service gibt seinen eigenen Backend-Host und sein Präfix an.
- **Service-Präfixe**: Die Endpunkte jedes Service werden automatisch unter ihrem jeweiligen Namen abgebildet, mit anpassbaren Überschreibungen.
- **„root"-Ausnahme**: Services mit dem Namen `root` (oder mit leerem Präfix) erhalten kein Präfix (ihre Endpunkte bleiben im Wurzelpfad).
- **Extra-Config-Injektion**: Fügen Sie globale und servicespezifische zusätzliche Plugin-Konfigurationen ein (wie Ratenbegrenzung oder JWT-Validierung).
- **Ersetzung von Umgebungs- und lokalen Variablen**: Leistungsstarke Injektion von Jinja2-Template-Variablen `{{ VAR_NAME }}` aus der Umgebung oder aus lokalen YAML-Variablen.
- **Erkennung von Datei-Uploads**: Spezielle Behandlung für `multipart/form-data`-Endpunkte.

## Verwendung

Erstellen Sie eine `krakend-builder.yaml`-Konfigurationsdatei, um Ihre Backend-Services und OpenAPI-Spezifikationen zuzuordnen.

```bash
python3 app.py -c krakend-builder.yaml -o output/krakend.json
```

### Builder-Konfiguration (krakend-builder.yaml)

```yaml
global:
  # Global configurations applied to all endpoints (e.g. Auth validators)
  extra_config: ./config/auth.json
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
```

### Extra Config (auth.json-Beispiel)

Sie können externe JSON-Konfigurationsdateien referenzieren, um KrakenD-Plugins anzuwenden. Die Jinja2-Template-Syntax `{{ VAR_NAME }}` wird unterstützt und aus dem `variables`-Block Ihres Builders oder aus den System-Umgebungsvariablen ersetzt:

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

### Umgebungsvariablen

| Variable | Standard | Beschreibung |
|----------|---------|-------------|
| `CONFIG_FILE` | `krakend-builder.yaml` | Pfad der Eingabe-Builder-YAML-Datei |
| `OUTPUT_FILE` | `krakend.json` | Pfad der generierten KrakenD-Konfigurationsdatei |

*Hinweis: Sie können auch beliebige Umgebungsvariablen übergeben, die Ihre `extra_config`-Dateien erwarten, wenn Sie sie nicht explizit in den `variables`-Blöcken des YAML definieren.*

### CLI-Optionen

```bash
python3 app.py [-h] [-c CONFIG] [-o OUTPUT]
```

## Anforderungen

### Python
- Python 3.9+
- PyYAML
- Jinja2

Installieren Sie die Abhängigkeiten:
```bash
pip install -r requirements.txt
```

### Docker (für Tests)
- Docker
- KrakenD-Image (für Validierungstests)

Das Test-Dockerfile lädt das KrakenD-Binary nativ herunter, um die Konfiguration zu validieren.

## Codequalität

Formatieren Sie mit black und prüfen Sie mit ruff:
```bash
black src/
ruff check src/
```

## Docker

### Produktions-Build
```bash
docker build -t swagger2krakend .
docker run -v $(pwd)/config:/config swagger2krakend python3 app.py -c /config/krakend-builder.yaml -o /config/krakend.json
```

### Test-Build
Erstellen und führen Sie die Tests mit nativer Validierung des KrakenD-Konfigurations-JSON aus:
```bash
docker build -t swagger2krakend-test -f Dockerfile.test .
docker run --rm swagger2krakend-test
```

## Exit-Codes

- `0`: Erfolg
- `1`: Fehler (fehlende Dateien, Parsing-Fehler, Syntaxfehler, fehlende Variablen)

## Mitwirken

Beiträge sind willkommen. In [CONTRIBUTING.md](../CONTRIBUTING.md) (auf Englisch)
erfahren Sie, wie Sie eine Entwicklungsumgebung einrichten, die
Qualitätsprüfungen ausführen und einen Pull Request eröffnen. Durch Ihre
Teilnahme erklären Sie sich damit einverstanden, unseren
[Verhaltenskodex](../CODE_OF_CONDUCT.md) (auf Englisch) einzuhalten.

## Sicherheit

Bitte melden Sie Sicherheitslücken verantwortungsvoll — siehe unsere
[Sicherheitsrichtlinie](../SECURITY.md) (auf Englisch). Bitte öffnen Sie
**keine** öffentlichen Issues für Sicherheitslücken.

## Lizenz

Lizenziert unter der [Apache-Lizenz 2.0](../LICENSE).
