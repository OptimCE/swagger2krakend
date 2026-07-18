<p align="center">
  <img src="logo.svg" alt="Logo swagger2krakend OptimCE" width="160">
</p>

# swagger2krakend

[![Site web](https://img.shields.io/badge/Site%20web-optimce.be-2e7d32.svg)](https://www.optimce.be)
[![Licence](https://img.shields.io/badge/Licence-Apache%202.0-blue.svg)](../LICENSE)
[![en](https://img.shields.io/badge/lang-en-lightgrey.svg)](../README.md)
[![fr](https://img.shields.io/badge/lang-fr-43a047.svg)](README.fr.md)
[![de](https://img.shields.io/badge/lang-de-lightgrey.svg)](README.de.md)
[![nl](https://img.shields.io/badge/lang-nl-lightgrey.svg)](README.nl.md)

Convertissez des fichiers Swagger/OpenAPI YAML en configuration de passerelle d'API KrakenD à l'aide d'un format de configuration déclaratif au format YAML.

## Fonctionnalités

- **Configuration YAML déclarative** : configurez toute la structure de votre passerelle d'API dans un seul fichier `krakend-builder.yaml`.
- **Mode multi-fichiers** : traitez plusieurs fichiers Swagger/OpenAPI en une seule configuration KrakenD unifiée.
- **Backends par service** : chaque service spécifie son propre hôte backend et son préfixe.
- **Préfixage des services** : les endpoints de chaque service sont automatiquement placés sous leur nom respectif, avec des surcharges personnalisables.
- **Exception « root »** : les services nommés `root` (ou avec un préfixe vide) n'ont pas de préfixe (leurs endpoints restent à la racine).
- **Injection d'extra-config** : injectez des configurations de plugins supplémentaires, globales et par service (comme la limitation de débit ou la validation JWT).
- **Substitution de variables d'environnement et locales** : injection puissante de variables de template Jinja2 `{{ VAR_NAME }}` depuis l'environnement ou des variables YAML locales.
- **Détection des envois de fichiers** : traitement spécial pour les endpoints `multipart/form-data`.

## Utilisation

Créez un fichier de configuration `krakend-builder.yaml` pour associer vos services backend et vos spécifications OpenAPI.

```bash
python3 app.py -c krakend-builder.yaml -o output/krakend.json
```

### Configuration du builder (krakend-builder.yaml)

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

### Extra Config (exemple auth.json)

Vous pouvez référencer des fichiers de configuration JSON externes pour appliquer des plugins KrakenD. La syntaxe de template Jinja2 `{{ VAR_NAME }}` est prise en charge et sera substituée depuis le bloc `variables` de votre builder ou depuis les variables d'environnement système :

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

### Variables d'environnement

| Variable | Valeur par défaut | Description |
|----------|---------|-------------|
| `CONFIG_FILE` | `krakend-builder.yaml` | Chemin du fichier YAML builder d'entrée |
| `OUTPUT_FILE` | `krakend.json` | Chemin du fichier de configuration KrakenD généré en sortie |

*Remarque : vous pouvez aussi passer toute variable d'environnement attendue par vos fichiers `extra_config` si vous ne les définissez pas explicitement dans les blocs `variables` du YAML.*

### Options de la CLI

```bash
python3 app.py [-h] [-c CONFIG] [-o OUTPUT]
```

## Prérequis

### Python
- Python 3.9+
- PyYAML
- Jinja2

Installez les dépendances :
```bash
pip install -r requirements.txt
```

### Docker (pour les tests)
- Docker
- Image KrakenD (pour les tests de validation)

Le Dockerfile de test récupère nativement le binaire KrakenD pour la validation de la configuration.

## Qualité du code

Formatez avec black et analysez avec ruff :
```bash
black src/
ruff check src/
```

## Docker

### Build de production
```bash
docker build -t swagger2krakend .
docker run -v $(pwd)/config:/config swagger2krakend python3 app.py -c /config/krakend-builder.yaml -o /config/krakend.json
```

### Build de test
Construisez et exécutez les tests avec la validation native du JSON de configuration KrakenD :
```bash
docker build -t swagger2krakend-test -f Dockerfile.test .
docker run --rm swagger2krakend-test
```

## Codes de sortie

- `0` : succès
- `1` : erreur (fichiers manquants, erreurs d'analyse, erreurs de syntaxe, variables manquantes)

## Contribuer

Les contributions sont les bienvenues. Consultez
[CONTRIBUTING.md](../CONTRIBUTING.md) (en anglais) pour savoir comment mettre en
place un environnement de développement, exécuter les contrôles qualité et
ouvrir une pull request. En participant, vous acceptez de respecter notre
[Code de conduite](../CODE_OF_CONDUCT.md) (en anglais).

## Sécurité

Merci de signaler les vulnérabilités de sécurité de manière responsable — voir
notre [politique de sécurité](../SECURITY.md) (en anglais). Merci de **ne pas**
ouvrir d'issues publiques pour les vulnérabilités.

## Licence

Distribué sous [licence Apache 2.0](../LICENSE).
