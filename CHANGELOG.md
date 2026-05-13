# Changelog

## [0.1.1] - 2026-05-13

### Added
- **`__repr__` for `DakeraStorage`**: meaningful string representation for easier debugging in CrewAI pipelines
- Community health files: `CONTRIBUTING.md`, `SECURITY.md`, issue templates, PR template

### Changed
- Bumped GitHub Actions: `actions/checkout` v4 → v6, `actions/setup-python` v5 → v6

## [0.1.0] - 2026-05-13

### Added
- Initial release — CrewAI integration for Dakera AI memory platform
- `DakeraStorage` class implementing CrewAI's `Storage` interface for persistent agent memory
- PyPI publish via OIDC Trusted Publisher
