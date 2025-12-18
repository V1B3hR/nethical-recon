# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Phase B implementation: Unified Data Model + Normalization
  - Created 7 Pydantic v2 domain models (Target, ScanJob, ToolRun, Evidence, Finding, Asset, IOC)
  - Implemented SQLAlchemy ORM with relationships and foreign keys
  - Set up Alembic for database migrations with initial schema
  - Added repository pattern for clean data access
  - Implemented SQLite as default backend with PostgreSQL support
  - Created parser interface for tool output normalization
  - Added Nmap XML parser with automatic severity assignment
  - Added full evidence provenance with SHA-256/MD5 checksums
  - Created 32 comprehensive tests (25 model + 7 parser tests)
  
- Phase A implementation: Foundation & Repo Professionalization
  - Created `pyproject.toml` for modern Python packaging
  - Set up `src/nethical_recon/` package structure
  - Added CLI entry point using Typer (`nethical` command)
  - Configured code quality tools: ruff, black, mypy
  - Set up pre-commit hooks for automated checks
  - Created CHANGELOG.md for release discipline
  - Added GitHub Actions CI/CD workflows
  - Integrated security scanning: Bandit, pip-audit

### Changed
- Migrated from manual setup to modern Python packaging standards
- Reorganized code structure to support better modularity
- Updated CLI from argparse to Typer framework with subcommands
- Added SQLAlchemy and Alembic as core dependencies

### Security
- Added automated security scanning in CI/CD pipeline
- Implemented pre-commit hooks to catch security issues early
- Added input validation on all domain models
- Implemented checksums for data integrity verification

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
