"""InfraOps Core reusable library."""

from importlib import metadata

try:
    __version__ = metadata.version("infraops-core")
except metadata.PackageNotFoundError:  # pragma: no cover - during local development
    __version__ = "0.0.0"

__all__ = ["__version__"]
