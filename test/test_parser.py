import sys

from swagger2krakend.parser import (
    DEFAULT_INPUT_HEADERS,
    _normalize_path_params,
    generate_krakend_config,
)


def _swagger(paths):
    return {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": paths,
    }


def _get_op(summary="op"):
    return {"get": {"summary": summary, "responses": {"200": {"description": "ok"}}}}


AUTH_GLOBAL = {"auth/validator": {"alg": "RS256", "jwk_url": "https://example.com/jwks.json"}}


def run_tests():
    try:
        # --- _normalize_path_params ---
        assert _normalize_path_params("/pharmacy/prices/{medicine_id}") == "/pharmacy/prices/{p1}"
        assert _normalize_path_params("/pharmacy/prices/{medicine_price_id}/price") == "/pharmacy/prices/{p1}/price"
        assert _normalize_path_params("/a/{x}/b/{y}") == "/a/{p1}/b/{p2}"
        assert _normalize_path_params("/health/liveness") == "/health/liveness"
        # Suffix params (e.g. ICS feed tokens) are not bare segments — untouched.
        assert _normalize_path_params("/feed/{token}.ics") == "/feed/{token}.ics"
        print("_normalize_path_params assertions passed")

        # --- Conflicting sibling params normalize to a conflict-free route set ---
        # /prices/{medicine_id} + /prices/{medicine_price_id}/price panics KrakenD's
        # gin router when passed verbatim (different param names, same position).
        swagger = _swagger(
            {
                "/prices/{medicine_id}": _get_op(),
                "/prices/{medicine_price_id}/price": _get_op(),
            }
        )
        config = generate_krakend_config(swagger, "http://backend:8000")
        endpoints = {e["endpoint"] for e in config["endpoints"]}
        assert endpoints == {"/prices/{p1}", "/prices/{p1}/price"}, f"unexpected endpoints: {endpoints}"
        for e in config["endpoints"]:
            assert e["backend"][0]["url_pattern"] == e["endpoint"], "url_pattern must match the normalized endpoint"
        print("conflicting param names normalized")

        # --- include_auth=False keeps the service public ---
        protected = generate_krakend_config(
            _swagger({"/things": _get_op()}), "http://b:80", global_extra_config=AUTH_GLOBAL
        )
        assert protected["endpoints"][0]["extra_config"]["auth/validator"] == AUTH_GLOBAL["auth/validator"]

        public = generate_krakend_config(
            _swagger({"/things": _get_op()}),
            "http://b:80",
            global_extra_config=AUTH_GLOBAL,
            include_auth=False,
        )
        assert "extra_config" not in public["endpoints"][0], "public service must not carry auth/validator"
        print("include_auth=False assertions passed")

        # --- non-auth global extra_config still merges into the root for public services ---
        mixed = generate_krakend_config(
            _swagger({"/things": _get_op()}),
            "http://b:80",
            global_extra_config={**AUTH_GLOBAL, "security/cors": {"allow_origins": ["http://localhost:4200"]}},
            include_auth=False,
        )
        assert mixed["extra_config"]["security/cors"]["allow_methods"] == [
            "GET",
            "POST",
            "PUT",
            "DELETE",
            "PATCH",
            "OPTIONS",
        ]
        assert mixed["extra_config"]["security/cors"]["allow_origins"] == ["http://localhost:4200"]
        fallback = generate_krakend_config(_swagger({}), "http://b:80")
        assert fallback["extra_config"]["security/cors"]["allow_origins"] == ["*"]
        print("non-auth global merge assertions passed")

        # --- input_headers override + default ---
        custom = generate_krakend_config(
            _swagger({"/things": _get_op()}), "http://b:80", input_headers=["Authorization"]
        )
        assert custom["endpoints"][0]["input_headers"] == ["Authorization"]
        default = generate_krakend_config(_swagger({"/things": _get_op()}), "http://b:80")
        assert default["endpoints"][0]["input_headers"] == DEFAULT_INPUT_HEADERS
        print("input_headers assertions passed")

        # --- timeout override + default ---
        assert generate_krakend_config(_swagger({}), "http://b:80")["timeout"] == "3000ms"
        assert generate_krakend_config(_swagger({}), "http://b:80", timeout="30s")["timeout"] == "30s"
        print("timeout assertions passed")

        print("All parser assertions passed!")
    except AssertionError as e:
        print(f"Test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_tests()
