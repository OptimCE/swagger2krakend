<p align="center">
  <img src="logo.svg" alt="swagger2krakend OptimCE-logo" width="160">
</p>

# swagger2krakend

[![Website](https://img.shields.io/badge/Website-optimce.be-2e7d32.svg)](https://www.optimce.be/nl/)
[![Licentie](https://img.shields.io/badge/Licentie-Apache%202.0-blue.svg)](../LICENSE)
[![en](https://img.shields.io/badge/lang-en-lightgrey.svg)](../README.md)
[![fr](https://img.shields.io/badge/lang-fr-lightgrey.svg)](README.fr.md)
[![de](https://img.shields.io/badge/lang-de-lightgrey.svg)](README.de.md)
[![nl](https://img.shields.io/badge/lang-nl-43a047.svg)](README.nl.md)

Converteer Swagger/OpenAPI-YAML-bestanden naar een KrakenD API-gateway-configuratie met behulp van een declaratief YAML-builderconfiguratieformaat.

## Functies

- **Declaratieve YAML-configuratie**: configureer de volledige structuur van uw API-gateway in één enkel `krakend-builder.yaml`-bestand.
- **Multi-bestandsmodus**: verwerk meerdere Swagger/OpenAPI-bestanden tot één verenigde KrakenD-configuratie.
- **Backends per service**: elke service geeft zijn eigen backend-host en prefix op.
- **Service-prefixen**: de endpoints van elke service worden automatisch onder hun respectieve naam geplaatst, met aanpasbare overschrijvingen.
- **„root"-uitzondering**: services met de naam `root` (of met een lege prefix) krijgen geen prefix (hun endpoints blijven op het hoofdpad).
- **Extra-config-injectie**: injecteer globale en servicespecifieke extra plugin-configuraties (zoals snelheidsbeperking of JWT-validatie).
- **Substitutie van omgevings- en lokale variabelen**: krachtige injectie van Jinja2-templatevariabelen `{{ VAR_NAME }}` vanuit de omgeving of lokale YAML-variabelen.
- **Detectie van bestandsuploads**: speciale behandeling voor `multipart/form-data`-endpoints.

## Gebruik

Maak een `krakend-builder.yaml`-configuratiebestand om uw backend-services en OpenAPI-specificaties te koppelen.

```bash
python3 app.py -c krakend-builder.yaml -o output/krakend.json
```

### Builder-configuratie (krakend-builder.yaml)

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

### Extra Config (auth.json-voorbeeld)

U kunt verwijzen naar externe JSON-configuratiebestanden om KrakenD-plugins toe te passen. De Jinja2-templatesyntaxis `{{ VAR_NAME }}` wordt ondersteund en wordt vervangen vanuit het `variables`-blok van uw builder of vanuit de systeemomgevingsvariabelen:

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

### Omgevingsvariabelen

| Variabele | Standaard | Beschrijving |
|----------|---------|-------------|
| `CONFIG_FILE` | `krakend-builder.yaml` | Pad van het invoer-builder-YAML-bestand |
| `OUTPUT_FILE` | `krakend.json` | Pad van het gegenereerde KrakenD-configuratiebestand |

*Opmerking: u kunt ook alle omgevingsvariabelen doorgeven die uw `extra_config`-bestanden verwachten als u ze niet expliciet definieert in de `variables`-blokken van de YAML.*

### CLI-opties

```bash
python3 app.py [-h] [-c CONFIG] [-o OUTPUT]
```

## Vereisten

### Python
- Python 3.9+
- PyYAML
- Jinja2

Installeer de afhankelijkheden:
```bash
pip install -r requirements.txt
```

### Docker (voor tests)
- Docker
- KrakenD-image (voor validatietests)

Het test-Dockerfile haalt het KrakenD-binary native op voor de validatie van de configuratie.

## Codekwaliteit

Formatteer met black en analyseer met ruff:
```bash
black src/
ruff check src/
```

## Docker

### Productie-build
```bash
docker build -t swagger2krakend .
docker run -v $(pwd)/config:/config swagger2krakend python3 app.py -c /config/krakend-builder.yaml -o /config/krakend.json
```

### Test-build
Bouw en voer de tests uit met native validatie van de KrakenD-configuratie-JSON:
```bash
docker build -t swagger2krakend-test -f Dockerfile.test .
docker run --rm swagger2krakend-test
```

## Exitcodes

- `0`: succes
- `1`: fout (ontbrekende bestanden, parseerfouten, syntaxisfouten, ontbrekende variabelen)

## Bijdragen

Bijdragen zijn welkom. Zie [CONTRIBUTING.md](../CONTRIBUTING.md) (in het Engels)
voor hoe u een ontwikkelomgeving opzet, de kwaliteitscontroles uitvoert en een
pull request opent. Door deel te nemen gaat u akkoord met onze
[Gedragscode](../CODE_OF_CONDUCT.md) (in het Engels).

## Beveiliging

Meld beveiligingsproblemen op een verantwoorde manier — zie ons
[beveiligingsbeleid](../SECURITY.md) (in het Engels). Open **geen** openbare
issues voor kwetsbaarheden.

## Licentie

Gelicentieerd onder de [Apache-licentie 2.0](../LICENSE).
