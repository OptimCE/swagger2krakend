# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.1.0] - 2026-07-26

### Added

- `global.passthrough` (default `false`): emit the `no-op` encoding on every
  endpoint, turning the gateway into a transparent reverse proxy that forwards
  the backend's status code, body and headers verbatim instead of letting
  KrakenD replace non-2xx responses with a bodyless 500 and collapse `201`/`202`
  into `200`. Trade-off: `no-op` bypasses the proxy pipe, so aggregation,
  merging, response manipulation, concurrent backends and backend-level
  `extra_config` no longer apply. Router-pipe features (`auth/validator`,
  `qos/ratelimit/router`, `security/cors`) are unaffected.
- `global.stream_timeout` (default unset): a longer per-endpoint timeout applied
  only to upload and file-download endpoints, so long-lived streams (SSE) and
  large exports are not cut off by the short global timeout. It keys off the
  kind of endpoint, not the encoding, so enabling `passthrough` does not hand it
  to the rest of the API.

Both keys are opt-in and default to the previous behaviour: a builder that sets
neither produces a byte-identical configuration.
