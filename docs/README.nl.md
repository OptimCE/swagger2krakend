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
- **Transparante proxymodus**: optionele `no-op`-codering op elk endpoint, die statuscodes, bodies en headers van de backend ongewijzigd doorgeeft.
- **Streaming-time-outs**: optionele langere time-out die alleen op upload- en bestandsdownload-endpoints wordt toegepast.

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

`auth` staat standaard op `true`. Stel `auth: false` in voor handmatig
geschreven publieke doorgangen zoals health-probes en documentatie-endpoints.
Padparameters worden positioneel genormaliseerd (`{p1}`, `{p2}`, ...) om
conflicten in de KrakenD-router te voorkomen wanneer routes op dezelfde
segmentpositie verschillende parameternamen gebruiken.

De generator biedt achterwaarts compatibele fallbackwaarden voor time-out,
doorgestuurde headers, logging, foutafhandeling en CORS. Gebruik
`global.timeout` en `global.input_headers` om de time-out en de request-headers
te overschrijven. Gebruik het globale extra-config-bestand om CORS-instellingen
te overschrijven; globale instellingen die niet met authenticatie te maken
hebben worden samengevoegd in de KrakenD-hoofdconfiguratie en lijstwaarden
vervangen de fallbacklijsten.

`global.stream_timeout` stelt een langere time-out per endpoint in, zodat
langlopende streams (SSE) en grote exports niet worden afgebroken door de korte
globale time-out. Deze wordt toegepast op basis van het *soort* endpoint —
uploads (`multipart/form-data`) en bestandsdownloads — en nooit op basis van de
codering, zodat het inschakelen van `passthrough` de streaming-time-out niet aan
de rest van de API geeft. Standaard is deze niet ingesteld en behouden alle
endpoints de globale time-out.

`global.passthrough` (standaard `false`) geeft op elk endpoint de
`no-op`-codering, waardoor de gateway een transparante reverse proxy wordt. Bij
elke andere codering vervangt KrakenD een niet-2xx-backendantwoord door zijn
eigen 500 zonder body en worden `201`/`202` teruggebracht tot `200`; `no-op`
geeft de status, body en headers van de backend ongewijzigd terug, wat van
belang is wanneer de backend al een gestructureerde foutenvelop gebruikt die de
client moet kunnen lezen. Daar staat tegenover dat `no-op` de proxy-pipeline
omzeilt: aggregatie, samenvoeging, responsmanipulatie, gelijktijdige backends en
`extra_config` op backendniveau werken niet meer. Functies van de
router-pipeline blijven onaangetast, dus `auth/validator` (en daarmee
`auth: false`), `qos/ratelimit/router` en `security/cors` blijven precies werken
zoals voorheen.

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
