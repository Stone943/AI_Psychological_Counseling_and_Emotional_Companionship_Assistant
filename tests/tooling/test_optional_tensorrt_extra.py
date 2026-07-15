"""Verify that TensorRT is only loaded conditionally on Linux x86_64.

On Windows and non-Linux platforms, importing mental_health_api must NOT
trigger any TensorRT or CUDA imports.
"""

from __future__ import annotations

import sys


def test_no_tensorrt_import_on_cpu() -> None:
    """Standard CPU import must not load TensorRT or CUDA modules."""
    # These modules should NOT be in sys.modules before or after import
    forbidden_prefixes = (
        "tensorrt",
        "tensorrt.",
        "cuda",
        "pycuda",
    )

    import mental_health_api

    _ = mental_health_api.__version__

    for mod_name in list(sys.modules.keys()):
        for prefix in forbidden_prefixes:
            assert not mod_name.lower().startswith(
                prefix
            ), f"TensorRT/CUDA module '{mod_name}' was imported during mental_health_api import"


def test_tensorrt_extra_is_optional() -> None:
    """The tensorrt extra should be a conditional dependency."""
    # On Windows/non-NVIDIA, attempting to import tensorrt should fail
    # This proves we didn't install the tensorrt extra
    try:
        import tensorrt  # noqa: F401  # type: ignore[import-untyped]

        # If we CAN import it, it must be Linux x86_64 with NVIDIA
        assert sys.platform == "linux", "TensorRT imported on non-Linux platform"
    except ImportError:
        # Expected on most platforms
        pass
