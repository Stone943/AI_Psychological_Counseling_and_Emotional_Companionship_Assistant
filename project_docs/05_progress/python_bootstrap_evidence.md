# Python Bootstrap Evidence — B-01

**Generated:** 2026-07-14
**Python version:** 3.10.20
**uv version:** 0.11.28
**Platform:** Windows 11 Home China x86_64
**Conda environment:** mental_health

## Bootstrap check items

| Check | Status | Notes |
|-------|--------|-------|
| `.python-version` exists | ✅ PASS | 3.10 |
| `uv.lock` exists | ✅ PASS | 151 packages resolved |
| `pyproject.toml` workspace | ✅ PASS | root + mental_health_api + mental_health_ai |
| `uv lock --check` passes | ✅ PASS | Lockfile up-to-date |
| `import mental_health_api` | ✅ PASS | v0.1.0 |
| `import mental_health_ai` | ✅ PASS | v0.1.0 |
| No TensorRT/CUDA import on CPU | ✅ PASS | Windows: expected |
| Docker compose.test.yml valid | ✅ PASS | 5 services declared |
| pytest (19 tests) | ✅ PASS | All 19 passed |
| ruff check | ✅ PASS | All checks passed |
| ruff format check | ✅ PASS | 13 files formatted |
| `deploy/compose.dev.yml` valid | ✅ PASS | 3 infra services |

## Package structure

```
src/
├── mental_health_api/          # B-owned FastAPI backend
│   ├── pyproject.toml
│   └── mental_health_api/
│       ├── __init__.py
│       ├── app.py              # FastAPI app factory
│       ├── config.py           # Strict Settings
│       └── errors.py           # AppError hierarchy
└── mental_health_ai/           # A-owned AI package (placeholder)
    ├── pyproject.toml
    └── mental_health_ai/
        └── __init__.py
```

## Commands

```bash
# Standard CPU bootstrap
uv sync --frozen --extra ai --extra onnx

# NVIDIA Linux only (incremental)
uv sync --frozen --extra ai --extra onnx --extra tensorrt

# Quality gate
uv lock --check
uv run ruff check src/mental_health_api/mental_health_api/ tests/ scripts/
uv run ruff format --check src/mental_health_api/mental_health_api/ tests/ scripts/
uv run pytest tests/api/test_app.py tests/api/test_config.py tests/integration/test_early_compose_contract.py tests/tooling/test_optional_tensorrt_extra.py -q
```

## Notes

- Python 3.10 used per project requirements (conda environment `mental_health`)
- pip configured with Tsinghua mirror: `https://pypi.tuna.tsinghua.edu.cn/simple`
- TensorRT/CUDA marker: `sys_platform == 'linux' and platform_machine == 'x86_64'`
- Windows platform: CPU-only baseline, TensorRT extra not installed
- GitHub remote: pending (network blocked, repo ready locally)
