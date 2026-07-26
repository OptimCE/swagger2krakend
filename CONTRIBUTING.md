# Contributing to OptimCE — swagger2krakend

Thank you for your interest in contributing! Issues and pull requests are
welcome from everyone. By participating in this project, you agree to abide by
our [Code of Conduct](CODE_OF_CONDUCT.md).

## Where to Contribute

This repository holds **swagger2krakend** — a small command-line tool that
converts Swagger/OpenAPI specifications into a KrakenD API gateway
configuration, driven by a single declarative `krakend-builder.yaml` file. It is
one of several repositories under the
[OptimCE organization](https://github.com/OptimCE), and is included in the
[OptimCE monorepo](https://github.com/OptimCE/monorepo) as a git submodule.

- **Changes to the generator itself** (the CLI, the Swagger parser, the KrakenD
  config builder, variable substitution, tests) belong here.
- **Changes to the running gateway** — the actual KrakenD configuration, Docker
  Compose, authentication (Keycloak), shared reference data — belong in the
  [monorepo](https://github.com/OptimCE/monorepo) instead.

## Setting Up a Development Environment

The tool targets **Python 3.9+**.

```bash
git clone https://github.com/OptimCE/swagger2krakend.git
cd swagger2krakend
python3 -m venv .venv && . .venv/Scripts/activate   # bash: source .venv/bin/activate
pip install -r requirements-dev.txt
```

Run the quality gates before opening a pull request:

```bash
ruff check . && black --check .
```

These are the tools configured in `pyproject.toml` (line length 120);
`uv run ruff check .` and `uv run black .` work too — see `AGENTS.md`.

Generated configurations are validated against the real KrakenD binary in
Docker, the same check CI runs:

```bash
docker build -f Dockerfile.test -t swagger2krakend-test .
docker run --rm swagger2krakend-test
```

This builds the sample configurations from `test/samples/`, runs `krakend check`
on each generated output, and executes the assertions in `test/test_output.py`.
The unit tests can also be run directly:

```bash
PYTHONPATH=src python3 test/test_config.py
PYTHONPATH=src python3 test/test_parser.py
PYTHONPATH=src python3 test/test_passthrough.py
```

New test files only run in CI once they are appended to the `CMD` chain in
`Dockerfile.test` — that chain is the entire test gate.

See the [README](README.md) for the builder configuration format, the CLI
options, and how the tool fits into the gateway.

## Reporting Bugs and Suggesting Features

Open a [GitHub issue](https://github.com/OptimCE/swagger2krakend/issues). For
bugs, include what you did, what you expected, and what happened instead — the
builder config, the input Swagger spec, and the generated output help a lot.

For security vulnerabilities, **do not open a public issue**; follow the
[security policy](SECURITY.md) instead.

## Submitting Pull Requests

1. Fork the repository and create a feature branch from `main`.
2. Make your changes. Keep each pull request focused on a single topic.
3. Make sure the quality gates pass (`ruff check . && black --check .`) and the
   Docker test build succeeds.
4. Open a pull request against `main`, describing **what** you changed and
   **why**.

Notes:

- Small documentation fixes are welcome as direct pull requests; for larger
  changes, opening an issue first to discuss the approach can save you time.

## Commit Messages

Use short, imperative commit messages, preferably following the
[Conventional Commits](https://www.conventionalcommits.org/) style used in this
repository:

```
feat: support per-service prefix override
fix: fall back to env var when a local variable is empty
chore: bump jinja2 to 3.1.6
docs: document the root service mapping
```

## License

swagger2krakend is licensed under the [Apache License 2.0](LICENSE). By
contributing, you agree that your contributions will be licensed under the same
license.
