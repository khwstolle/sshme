"""
Shared data models.
"""

import dataclasses

__all__ = ["HostInfo"]


@dataclasses.dataclass(frozen=True)
class HostInfo:
    name: str
    hostname: str | None = None
    port: int | None = None
    user: str | None = None
    description: str | None = None
    ssh_config_host: bool = False

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("HostInfo.name must not be empty")
        if self.port is not None and not (1 <= self.port <= 65535):
            raise ValueError(f"port {self.port!r} is out of range [1, 65535]")
