import os
import sys

from swagger2krakend.config import MissingEnvVarError, substitute_env_vars


def _restore_env(original_values):
    for key, value in original_values.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


def run_tests():
    keys = ["KEYCLOAK_URL", "REALM_NAME", "ISSUER", "REQUIRED_VAR"]
    original_values = {key: os.environ.get(key) for key in keys}

    try:
        os.environ["KEYCLOAK_URL"] = "http://env-keycloak:8080"
        os.environ["REALM_NAME"] = "env-realm"
        os.environ["ISSUER"] = "http://env.example/issuer"
        os.environ.pop("REQUIRED_VAR", None)

        jwk_url_template = "{{ KEYCLOAK_URL }}/realms/" "{{ REALM_NAME }}/protocol/openid-connect/certs"

        template = {
            "auth/validator": {
                "jwk_url": jwk_url_template,
                "issuer": "{{ ISSUER }}",
            }
        }

        resolved = substitute_env_vars(
            template,
            {
                "KEYCLOAK_URL": "",
                "REALM_NAME": None,
                "ISSUER": "http://local.example/issuer",
            },
        )

        validator = resolved["auth/validator"]
        expected_jwk_url = "http://env-keycloak:8080/realms/" "env-realm/protocol/openid-connect/certs"
        expected_issuer = "http://local.example/issuer"

        assert (
            validator["jwk_url"] == expected_jwk_url
        ), "Empty builder variables should fall back to environment values"
        assert validator["issuer"] == expected_issuer, "Non-empty builder variables should win"

        try:
            substitute_env_vars("{{ REQUIRED_VAR }}", {})
        except MissingEnvVarError:
            pass
        else:
            assert False, "Missing variables should still raise an error"
        print("All config substitution assertions passed!")
    except AssertionError as error:
        print(f"Test failed: {error}")
        sys.exit(1)
    finally:
        _restore_env(original_values)


if __name__ == "__main__":
    run_tests()
