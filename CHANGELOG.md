# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Phase A implementation: Foundation & Repo Professionalization
  - Created `pyproject.toml` for modern Python packaging
  - Set up `src/nethical_recon/` package structure
  - Added CLI entry point using Typer (`nethical` command)
  - Configured code quality tools: ruff, black, mypy
  - Set up pre-commit hooks for automated checks
  - Created CHANGELOG.md for release discipline
  - Added GitHub Actions CI/CD workflows
  - Integrated security scanning: Bandit, pip-audit

- Phase B implementation: Unified Data Model + Normalization
  - Created Pydantic v2 domain models for core entities
    - `Target`: Domain/IP/CIDR with scope and authorization tracking
    - `ScanJob`: Orchestration of multiple tool runs
    - `ToolRun`: Individual tool execution tracking with provenance
    - `Evidence`: Audit trail with cryptographic hashes
    - `Finding`: Normalized security findings from all tools
    - `Asset`: Discovered infrastructure (hosts, services, URLs)
    - `IOC`: Indicators of Compromise for threat intelligence
  - Implemented SQLAlchemy storage layer
    - Support for SQLite (development default) and PostgreSQL
    - DatabaseManager for database operations
    - Comprehensive database schema with indexes
  - Added evidence and provenance tracking
    - UTC timestamps for all events
    - Tool version tracking
    - Command line recording
    - SHA256 hash calculation for integrity
    - Chain of custody fields
  - Added dependencies: SQLAlchemy >=2.0.0, Alembic >=1.13.0
  - Created comprehensive test suite
    - 11 unit tests for domain models
    - 3 integration tests for storage layer
    - 100% test pass rate

### Changed
- Migrated from manual setup to modern Python packaging standards
- Reorganized code structure to support better modularity
- Updated pyproject.toml with database dependencies

### Security
- Added automated security scanning in CI/CD pipeline
- Implemented pre-commit hooks to catch security issues early
- Added cryptographic hash validation for evidence files
- Implemented chain of custody tracking

## [0.1.0] - 2025-12-16

### Added
- Initial version with Phase A foundation complete
- All 9 FALA phases from previous development
- AI-powered threat intelligence and analysis
- Bird surveillance system (Eagle, Falcon, Owl, Sparrow)
- Forest metaphor for infrastructure visualization
- Multi-backend database support
- Silent threat marking system
- Comprehensive sensor and camera systems
- Nanobot automated response system

[Unreleased]: https://github.com/V1B3hR/nethical-recon/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/V1B3hR/nethical-recon/releases/tag/v0.1.0
