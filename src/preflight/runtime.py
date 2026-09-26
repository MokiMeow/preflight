"""Connected runtime is installed only with explicit operator configuration."""
from .service import UnconfiguredRuntime


def build_runtime(settings):
    if not settings.creation_authorized:
        return UnconfiguredRuntime()
    # Production adapter composition is added after its isolated interface is integrated.
    raise RuntimeError("CONNECTED_ADAPTER_NOT_INTEGRATED")
