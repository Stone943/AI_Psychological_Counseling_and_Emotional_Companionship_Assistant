# Tooling Compatibility Evidence (B-owned)

**Date:** 2026-07-14

## B Toolchain Results

| Tool | Version | Status | Command |
|------|---------|--------|---------|
| Python | 3.10.20 | ✅ | `python --version` |
| uv | 0.11.28 | ✅ | `uv --version` |
| FastAPI | 0.115.14 | ✅ | `uv run python -c "import fastapi"` |
| pytest | 9.1.1 | ✅ | `uv run pytest --version` |
| ruff | 0.15.21 | ✅ | `uv run ruff --version` |
| mypy | 2.3.0 | ✅ | `uv run mypy --version` |
| Docker | - | ⚠️ | Windows dev; Linux CI required |
| Git | - | ✅ | `git --version` |

## IDE Compatibility

| IDE | Status | Notes |
|-----|--------|-------|
| VSCode | ✅ | `.vscode/settings.example.json` available |
| PyCharm | ✅ | Same uv/pytest/Ruff/mypy commands |

## CARLA Dependency Scan

| Surface | Result |
|---------|--------|
| Python deps | 0 CARLA hits |
| Node deps | N/A |
| Docker images | 0 CARLA hits |
| Compose services | 0 CARLA hits |
| SBOM | 0 CARLA hits |

## External Evidence References

| Evidence | Owner | Status |
|----------|-------|--------|
| AI model manifest | A | pending_external_evidence |
| AI performance profile | A | pending_external_evidence |
| Client Detox harness | C | pending_external_evidence |
| Client tooling evidence | C | pending_external_evidence |
