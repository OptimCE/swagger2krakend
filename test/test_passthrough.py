import sys

from swagger2krakend.parser import generate_krakend_config

# Two endpoints, one of each kind: a normal JSON route and a file download. The
# download is what pins the `stream_timeout` behaviour, which is the regression
# that `passthrough` could silently cause.
SWAGGER = {
    "info": {"title": "Test API"},
    "paths": {
        "/orders": {
            "get": {
                "responses": {"200": {"content": {"application/json": {"schema": {"type": "object"}}}}},
            }
        },
        "/orders/export": {
            "get": {
                "responses": {"200": {"content": {"application/pdf": {}}}},
            }
        },
    },
}

HOST = "http://backend:8080"
STREAM_TIMEOUT = "3600s"


def _by_path(config):
    return {endpoint["endpoint"]: endpoint for endpoint in config["endpoints"]}


def run_tests():
    try:
        # --- Default (passthrough off) keeps the historical behaviour ---------------
        default = _by_path(generate_krakend_config(SWAGGER, api_host=HOST, stream_timeout=STREAM_TIMEOUT))

        assert default["/orders"]["output_encoding"] == "json", "JSON routes must stay json by default"
        assert default["/orders"]["backend"][0]["encoding"] == "json", "backend encoding must match the endpoint"
        assert default["/orders/export"]["output_encoding"] == "no-op", "File downloads must always be no-op"
        print("Verified default encodings are unchanged")

        # --- passthrough=True makes every endpoint a transparent proxy --------------
        through = _by_path(
            generate_krakend_config(SWAGGER, api_host=HOST, stream_timeout=STREAM_TIMEOUT, passthrough=True)
        )

        for path, endpoint in through.items():
            assert endpoint["output_encoding"] == "no-op", f"{path} should be no-op under passthrough"
            assert endpoint["backend"][0]["encoding"] == "no-op", f"{path} backend should be no-op under passthrough"
        print("Verified passthrough emits no-op everywhere")

        # --- The regression: stream_timeout must not leak onto normal endpoints -----
        # `stream_timeout` used to key off `encoding == "no-op"`. Under passthrough
        # that is now true for EVERY endpoint, so keying off the encoding would hand
        # the hour-long streaming timeout to the whole API and quietly delete the
        # short global timeout that guards it.
        assert "timeout" not in through["/orders"], "stream_timeout must not apply to a normal JSON endpoint"
        assert (
            through["/orders/export"]["timeout"] == STREAM_TIMEOUT
        ), "stream_timeout must still apply to file downloads under passthrough"
        print("Verified stream_timeout still targets only streaming endpoints")

        print("All passthrough assertions passed!")
    except AssertionError as error:
        print(f"Test failed: {error}")
        sys.exit(1)


if __name__ == "__main__":
    run_tests()
