import json
import sys


def run_tests():
    try:
        with open("test/output/krakend-output.json", "r") as f:
            config = json.load(f)

        endpoints = config.get("endpoints", [])
        assert len(endpoints) > 0, "No endpoints generated"

        orders_endpoints = [e for e in endpoints if e["endpoint"].startswith("/orders")]
        users_endpoints = [e for e in endpoints if e["endpoint"].startswith("/users")]

        assert len(orders_endpoints) > 0, "No /orders endpoints found"
        assert len(users_endpoints) > 0, "No /users endpoints found"

        for endpoint in orders_endpoints:
            extra_config = endpoint.get("extra_config", {})
            assert "qos/ratelimit/router" in extra_config, f"qos/ratelimit/router missing in {endpoint['endpoint']}"
            assert extra_config["qos/ratelimit/router"]["max_rate"] == 100
            print(f"Verified custom config on {endpoint['endpoint']}")

        for endpoint in users_endpoints:
            extra_config = endpoint.get("extra_config", {})
            assert (
                "qos/ratelimit/router" not in extra_config
            ), f"qos/ratelimit/router should not be in {endpoint['endpoint']}"
            print(f"Verified NO custom config on {endpoint['endpoint']}")

        print("All assertions passed!")
    except AssertionError as e:
        print(f"Test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_tests()
